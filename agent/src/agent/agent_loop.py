from openai import OpenAI
from memory import Memory
import os

client = OpenAI(base_url=os.environ["LLM_URL"], api_key="ollama")
MODEL = os.environ["MODEL"]
MEMORY_DB = os.environ.get("MEMORY_DB", "memory.db")

SYSTEM_PROMPT = """You are Melody, the assistant of a musical instrument store called Empório da Música.

You help customers:
- find products (search_products)
- check their orders (get_orders)
- request returns (request_return)
- talk to a human (escalate_to_human)

Rules:
1. Only state product, price, stock or order details that come from a tool result. Never invent them.
2. The catalog is in Portuguese: always call search_products with Portuguese terms, even if the user writes in another language.
3. Before any action that changes something (like a return), summarize it and ask the user to confirm.
4. Call escalate_to_human when the user asks for a person, is upset, or you can't solve the problem after two tries.
5. If a request is unrelated to the store, politely say you can only help with the store.
6. Reply in the user's language. Keep answers short and friendly.
"""

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
