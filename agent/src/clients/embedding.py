import os

from openai import OpenAI

# the embedding service (llama.cpp) speaks the OpenAI API, same as the LLM client
client = OpenAI(base_url=os.environ["EMBEDDING_URL"], api_key="none")


def embed(texts):
    response = client.embeddings.create(model="bge-m3", input=texts)
    return [item.embedding for item in response.data]  # one vector per text, in the same order
