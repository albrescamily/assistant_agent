import os

from openai import OpenAI

# Ollama speaks the OpenAI API at /v1; the key is required by the SDK but not checked
client = OpenAI(base_url=os.environ["LLM_URL"], api_key="ollama")
