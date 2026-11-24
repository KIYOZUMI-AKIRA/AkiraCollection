from dotenv import load_dotenv
from openai import OpenAI
import os


load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
print(api_key)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.ai/v1",
)