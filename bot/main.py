import asyncio
import base64
import logging
import os
import sys

import redis.asyncio as redis
from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from amplitude import Amplitude, BaseEvent

from concurrency import executor
from database.models import save_value, get_all_pr_faqs
from environment import Settings
from llm.client import client
from llm.filework import setup_filework
from pr_faq.actions import manage_pr_faq, is_pr_faq
from tools import bot, router, download_voice_as_text, send_voice, get_thread_id

pool = redis.ConnectionPool.from_url("redis://redis:6379")
redis_client = redis.Redis.from_pool(pool)
redis_storage = RedisStorage(redis_client)

amplitude_client = Amplitude(api_key=Settings().AMPLITUDE_API_KEY)

assistant_id = Settings().ASSISTANT_ID

counter = 0


class Form(StatesGroup):
    main = State()
    pr_faq = State()


@router.message(Command("pr_faq"))
async def on_pr_faq_command(message: Message, state: FSMContext):
    await state.set_state(Form.pr_faq)
    print("PRFAQScene")
    await message.answer(text="Send a voice message describing idea for your start-up.")
    messages = [{
        "role": "system",
        "content": "User will now share an idea for a start-up with you. Your goal is to create a PR FAQ for it. "
                   "Ask all necessary questions to fully understand the idea, "
                   "goals and realisation plan of the project. "
                   "Try not to ask a lot of questions at once. "
                   "When you understand everything and are ready to generate PR FAQ, "
                   "then output it as a single message right in the way it's supposed to look like. "
                   "WITHOUT ANY FORMATTING AND WITHOUT ANY ADDITIONAL NOTED, QUESTIONS, ETC."
                   "The final PR FAQ must not exceed 2000 symbols. "
    }]
    await state.update_data(messages=messages)


@router.message(Form.pr_faq, F.voice)
async def on_message(message: Message, state: FSMContext):
    print("generating pr faq response...")

    data = await state.get_data()
    messages = data['messages']

    text = await download_voice_as_text(message.voice)

    messages.append({
        "role": "user",
        "content": text
    })
    completion = await client.chat.completions.create(
        messages=messages,
        model="gpt-4o",
    )
    response = completion.choices[0].message.content

    if await is_pr_faq(text=response):
        print(f"FINAL PR FAQ:\n{response}")
        await message.answer(text="PR FAQ has been successfully generated.")
        await manage_pr_faq(user_id=message.from_user.id, text=response)
        await state.set_state(Form.main)
        await state.update_data(messages=[])
        return

    await send_voice(text=response, chat_id=message.from_user.id)


@router.message(Command("my_pr_faqs"))
async def show_pr_faqs(message: Message):
    text = "Here are your PR FAQs:\n\n"
    pr_faqs = await get_all_pr_faqs(user_id=message.chat.id)
    for pr_faq in pr_faqs:
        text += f"{pr_faq.title}\n{pr_faq.url}\n\n"
    await message.answer(text=text)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


async def find_citations(message_content) -> str | None:
    annotations = message_content.annotations
    citations = []
    for annotation in annotations:
        message_content.value = message_content.value.replace(annotation.text, "")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = await client.files.retrieve(file_citation.file_id)
            citations.append(cited_file.filename)
    if citations:
        return citations[0]


@router.message(Form.main, F.voice)
async def on_voice(message: Message, state: FSMContext) -> None:
    event = BaseEvent(event_type="Send voice", user_id=str(message.from_user.id))
    executor.submit(amplitude_client.track, event)

    thread_id = await get_thread_id(state)

    transcription = await download_voice_as_text(voice=message.voice)

    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=transcription,
    )

    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    if run.status == 'requires_action':
        tool_outputs = []
        tasks = []
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            value = eval(tool.function.arguments)['value']
            tasks.append(save_value(user=message.chat.id, value=value))
            tool_outputs.append({'tool_call_id': tool.id, 'output': ""})
        run_coroutine = client.beta.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs,
        )
        results = await asyncio.gather(run_coroutine, *tasks)
        run = results[0]
    if run.status != 'completed':
        await message.answer("Something went wrong. Please try again.")
        return

    messages = await client.beta.threads.messages.list(
        thread_id=thread_id,
    )
    response = messages.data[0].content[0].text

    cited_file_name = await find_citations(message_content=response)

    await send_voice(text=response.value, chat_id=message.chat.id)

    if cited_file_name:
        await message.answer(text=f"Source: {cited_file_name}")


async def process_image(base64_image) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Here is my photo. Analyse the mood and answer correspondingly. "
                                             "Remember that you will lose access to photo once you answer."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    event = BaseEvent(event_type="Send photo", user_id=str(message.from_user.id))
    executor.submit(amplitude_client.track, event)

    thread_id = await get_thread_id(state)

    photo = message.photo[0]
    file = await bot.get_file(photo.file_id)
    path = f"{message.from_user.id}_{message.message_id}.jpg"
    await bot.download_file(file.file_path, path)
    base64_image = encode_image(path)
    os.remove(path)

    answer = await process_image(base64_image)

    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Here is my photo",
    )

    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="assistant",
        content=answer
    )

    print("response=" + answer)
    await send_voice(text=answer, chat_id=message.chat.id)


@router.message(CommandStart())
async def on_command_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.main)
    await message.answer("This is a voice assistant bot.\n"
                         "GitHub: https://github.com/request3301/telegram-voice-assistant")


def create_dispatcher():
    dispatcher = Dispatcher(
        storage=redis_storage,
    )
    dispatcher.include_router(router)

    return dispatcher


async def main() -> None:
    dp = create_dispatcher()
    await setup_filework()
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
