from openai import OpenAI
from agent.memory import Memory
import os
from prompts.system_prompts import SYSTEM_PROMPT
from tools.tools import TOOLS
from agent.executor import run_tool

client = OpenAI(base_url=os.environ["LLM_URL"], api_key="ollama")
MODEL = os.environ["MODEL"]
MEMORY_DB = os.environ.get("MEMORY_DB", "memory.db")



def chat(message, session_id):
    memory = Memory(MEMORY_DB, session_id)
    history = memory.load_history()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]
    stream = client.chat.completions.create(
        model=MODEL, messages=messages, reasoning_effort="none", stream=True,tools = TOOLS)

    reply = []
    tool_calls = {}  # when streaming, a tool call can arrive in pieces, so we join them by index
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

    if tool_calls:
        # the model needs to see its own request and then each result, in this order
        messages.append({
            "role": "assistant",
            "tool_calls": [
                {"id": call["id"], "type": "function",
                 "function": {"name": call["name"], "arguments": call["arguments"]}}
                for call in tool_calls.values()
            ],
        })
        for call in tool_calls.values():
            result = run_tool(call["name"], call["arguments"])
            print(f"tool {call['name']}({call['arguments']}) -> {result}")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

        # second call: no tools, so the model has to answer with text using the results
        stream = client.chat.completions.create(
            model=MODEL, messages=messages, reasoning_effort="none", stream=True)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                reply.append(text)
                yield text

    memory.save_exchange(message, "".join(reply))
