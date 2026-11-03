import os

from openai import OpenAI

# the embedding service (llama.cpp) speaks the OpenAI API, same as the LLM client in the agent
client = OpenAI(base_url=os.environ.get("EMBEDDING_URL", "http://localhost:8080/v1"), api_key="none")


def embed(texts):
    response = client.embeddings.create(model="bge-m3", input=texts)
    return [item.embedding for item in response.data]  # one vector per text, in the same order
