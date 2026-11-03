from agent.memory import Memory
import os
import re
from clients.llm import client
from prompts.system_prompts import build_system_prompt
from tools.registry import TOOLS
from agent.executor import run_tool

MODEL = os.environ["MODEL"]
MEMORY_DB = os.environ.get("MEMORY_DB", "memory.db")

RETRY_INSTRUCTION = "You wrote a price without a tool result in this turn. Call check_product or search_products before answering."
FALLBACK_REPLY = "Deixa eu confirmar esse valor no sistema: qual produto você quer consultar?"


def invented_price(answer):
    # a price ("R$" followed by a number) in an answer that called no tool can only have come from the model's head
    return not answer.tool_calls and re.search(r"R\$\s*\d", answer.content or "") is not None


def first_answer(messages):
    # not streamed: the whole answer has to exist before we can check it
    response = client.chat.completions.create(
        model=MODEL, messages=messages, reasoning_effort="none", tools=TOOLS)
    return response.choices[0].message


def chat(message, session_id):
    memory = Memory(MEMORY_DB, session_id)
    history = memory.load_history()

    messages = [
        {"role": "system", "content": build_system_prompt()},
        *history,
        {"role": "user", "content": message},
    ]

    answer = first_answer(messages)
    if invented_price(answer):
        print(f"invented price, retrying: {answer.content!r}")
        messages.append({"role": "system", "content": RETRY_INSTRUCTION})
        answer = first_answer(messages)

    reply = []
    if not answer.tool_calls:
        # checked before sending: if the retry still made a price up, the customer gets the safe reply instead
        text = FALLBACK_REPLY if invented_price(answer) else answer.content or ""
        reply.append(text)
        yield text
    else:
        # the model needs to see its own request and then each result, in this order
        messages.append({
            "role": "assistant",
            "tool_calls": [
                {"id": call.id, "type": "function",
                 "function": {"name": call.function.name, "arguments": call.function.arguments}}
                for call in answer.tool_calls
            ],
        })
        for call in answer.tool_calls:
            result = run_tool(call.function.name, call.function.arguments)
            print(f"tool {call.function.name}({call.function.arguments}) -> {result}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        # second call: no tools, so the model has to answer with text using the results
        stream = client.chat.completions.create(
            model=MODEL, messages=messages, reasoning_effort="none", stream=True)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                reply.append(text)
                yield text

    memory.save_exchange(message, "".join(reply))
