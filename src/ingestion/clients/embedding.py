import os

from openai import OpenAI

client = OpenAI(base_url=os.environ.get("EMBEDDING_URL", "http://localhost:8080/v1"), api_key="none")


def embed(texts):
    response = client.embeddings.create(model="bge-m3", input=texts)
    return [item.embedding for item in response.data] 