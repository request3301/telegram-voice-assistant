import asyncio
import logging
import sys
import os
import base64

from uuid import uuid4

from openai import AsyncOpenAI

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from environment import Settings
from values import save_value

from amplitude import Amplitude, BaseEvent
from concurrency import executor

amplitude_client = Amplitude(api_key=Settings().AMPLITUDE_API_KEY)

client = AsyncOpenAI(api_key=Settings().OPENAI_API_KEY)

bot = Bot(token=Settings().TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

assistant_id = Settings().ASSISTANT_ID

router = Router(name=__name__)
dp = Dispatcher()
dp.include_router(router)

counter = 0


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


async def send_audio(text: str, chat_id: int):
    filename = str(uuid4())
    audio_response = await client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    with open(filename + '.mp3', 'wb') as audio_file:
        audio_file.write(audio_response.read())
        audio_file.close()
    audio_file = FSInputFile(filename + '.mp3')
    await bot.send_voice(chat_id=chat_id, voice=audio_file)
    os.remove(filename + '.mp3')


@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext) -> None:
    event = BaseEvent(event_type="Send voice", user_id=str(message.from_user.id))
    executor.submit(amplitude_client.track, event)

    voice = message.voice
    await bot.download(voice, str(voice.file_id) + '.mp3')
    audio_file = open(str(voice.file_id) + '.mp3', 'rb')
    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    audio_file.close()
    print(transcription)

    data = await state.get_data()
    if 'thread' in data:
        thread = data['thread']
    else:
        thread = await client.beta.threads.create()
    await client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=transcription.text,
    )
    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
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
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs,
        )
        results = await asyncio.gather(run_coroutine, *tasks)
        run = results[0]
    if run.status != 'completed':
        await message.answer("Something went wrong. Please try again.")
        os.remove(str(voice.file_id) + '.mp3')
        return
    messages = await client.beta.threads.messages.list(
        thread_id=thread.id
    )
    response = messages.data[0].content[0].text.value

    print("response="+response)
    await send_audio(text=response, chat_id=message.chat.id)

    await state.update_data(thread=thread)


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

    data = await state.get_data()
    if 'thread' in data:
        thread = data['thread']
    else:
        thread = await client.beta.threads.create()

    photo = message.photo[0]
    file = await bot.get_file(photo.file_id)
    path = f"{message.from_user.id}_{message.message_id}.jpg"
    await bot.download_file(file.file_path, path)
    base64_image = encode_image(path)
    os.remove(path)

    answer = await process_image(base64_image)

    await client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Here is my photo",
    )

    await client.beta.threads.messages.create(
        thread_id=thread.id,
        role="assistant",
        content=answer
    )

    print("response=" + answer)
    await send_audio(text=answer, chat_id=message.chat.id)

    await state.update_data(thread=thread)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
