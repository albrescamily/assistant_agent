from agent.memory import Memory
from agent.session_log import log_turn
import os
import re
from opentelemetry import trace
from clients.llm import client
from prompts.system_prompts import build_system_prompt
from tools.registry import TOOLS
from agent.executor import run_tool

MODEL = os.environ["MODEL"]
MEMORY_DB = os.environ.get("MEMORY_DB", "memory.db")

RETRY_INSTRUCTION = "You wrote a price without a tool result in this turn. Call check_product or search_products before answering."
FALLBACK_REPLY = "Deixa eu confirmar esse valor no sistema: qual produto você quer consultar?"
MAX_ROUNDS = 4  # tool rounds per message; stops a model that keeps asking for tools forever


def invented_price(answer):
    # a price ("R$" followed by a number) in an answer that called no tool can only have come from the model's head
    return not answer.tool_calls and re.search(r"R\$\s*\d", answer.content or "") is not None


def first_answer(messages):
    # not streamed: the whole answer has to exist before we can check it
    response = client.chat.completions.create(
        model=MODEL, messages=messages, reasoning_effort="none", tools=TOOLS)
    return response.choices[0].message


def add_tool_results(messages, tool_calls):
    # the model needs to see its own request and then each result, in this order
    messages.append({
        "role": "assistant",
        "tool_calls": [
            {"id": call["id"], "type": "function",
             "function": {"name": call["name"], "arguments": call["arguments"]}}
            for call in tool_calls
        ],
    })
    for call in tool_calls:
        result = run_tool(call["name"], call["arguments"])  # run_tool already records a span with the arguments and the result
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})


def stream_round(messages, reply, use_tools):
    extra = {"tools": TOOLS} if use_tools else {}
    stream = client.chat.completions.create(
        model=MODEL, messages=messages, reasoning_effort="none", stream=True, **extra)

    tool_calls = {}
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            reply.append(delta.content)
            yield delta.content
        for call in delta.tool_calls or []:
            current = tool_calls.setdefault(call.index, {"id": "", "name": "", "arguments": ""})
            if call.id:
                current["id"] = call.id
            if call.function and call.function.name:
                current["name"] += call.function.name
            if call.function and call.function.arguments:
                current["arguments"] += call.function.arguments
    return list(tool_calls.values())


def chat(message, session_id):
    memory = Memory(MEMORY_DB, session_id)
    history = memory.load_history()

    messages = [
        {"role": "system", "content": build_system_prompt()},
        *history,
        {"role": "user", "content": message},
    ]

    turn_start = len(messages)  # everything appended after this is what the model did in this turn
    discarded_answer = None

    answer = first_answer(messages)
    if invented_price(answer):
        # an event on the request's span in Phoenix, with the answer the customer never saw
        trace.get_current_span().add_event("guardrail.invented_price", {"discarded_answer": answer.content or ""})
        discarded_answer = answer.content
        messages.append({"role": "system", "content": RETRY_INSTRUCTION})
        answer = first_answer(messages)

    tool_calls = [{"id": call.id, "name": call.function.name, "arguments": call.function.arguments}
                  for call in answer.tool_calls or []]

    reply = []
    if not tool_calls:
        # checked before sending: if the retry still made a price up, the customer gets the safe reply instead
        text = FALLBACK_REPLY if invented_price(answer) else answer.content or ""
        reply.append(text)
        yield text
    else:
        # once a tool has run, the answer is built on tool results, so it can be streamed safely;
        # each round the model sees the results and can ask for another tool (order -> return policy)
        for round_number in range(1, MAX_ROUNDS + 1):
            add_tool_results(messages, tool_calls)
            use_tools = round_number < MAX_ROUNDS  # last round: no tools, so the model has to answer with text
            tool_calls = yield from stream_round(messages, reply, use_tools)
            if not tool_calls:
                break

    memory.save_exchange(message, "".join(reply))
    # tool calls, tool results and retry instructions, in the order they happened
    log_turn(session_id, message, {"discarded_answer": discarded_answer, "steps": messages[turn_start:]}, "".join(reply))
