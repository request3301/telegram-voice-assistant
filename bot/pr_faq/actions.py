from database.models import save_pr_faq
from llm.client import client, model
from notion.actions import create_page
from tools import bot


async def manage_pr_faq(user_id: int, text: str):
    title = await generate_title(text)
    url = await create_page(title=title, text=text)
    await bot.send_message(chat_id=user_id, text=url)
    await save_pr_faq(user_id=user_id, title=title, url=url)


async def generate_title(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "You should generate a title for the provided start-up PR FAQ. "
                       "DO NOT USE ANY FORMATTING. DO NOT OUTPUT ANYTHING ELSE EXCEPT FOR A TITLE."
        },
        {
            "role": "user",
            "content": text
        },
    ]
    completion = await client.chat.completions.create(
        messages=messages,
        model=model,
    )
    response = completion.choices[0].message.content
    return response


async def is_pr_faq(text: str) -> bool:
    messages = [
        {
            "role": "system",
            "content": "Your objective is to determine whether or not the text user sends is a PR FAQ. "
                       "If it is, output 1. If not, output a 0. "
                       "DO NOT OUTPUT ANYTHING ELSE. "
        },
        {
            "role": "user",
            "content": text
        },
    ]
    completion = await client.chat.completions.create(
        messages=messages,
        model=model,
    )
    response = completion.choices[0].message.content
    if response == "1":
        return True
    return False
