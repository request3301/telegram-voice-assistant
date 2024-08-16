from openai import AsyncOpenAI

from environment import Settings

client = AsyncOpenAI(api_key=Settings().OPENAI_API_KEY)

model = "gpt-4o"
