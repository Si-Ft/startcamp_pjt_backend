from openai import OpenAI
import inspect
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

print(inspect.signature(client.responses.create))