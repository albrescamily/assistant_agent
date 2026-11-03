from openai import OpenAI
from agent.memory import Memory
import os
from prompts.system_prompts import SYSTEM_PROMPT

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
        model=MODEL, messages=messages, reasoning_effort="none", stream=True)

    reply = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            reply.append(text)
            yield text

    memory.save_exchange(message, "".join(reply))
