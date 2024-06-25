import asyncio
import logging
import sys
import os

from openai import AsyncOpenAI

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

bot = Bot(token=settings.TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

assistant_id = settings.ASSISTANT_ID

router = Router(name=__name__)
dp = Dispatcher()
dp.include_router(router)


@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext) -> None:
    voice = message.voice
    await bot.download(voice, str(voice.file_id) + '.mp3')
    audio_file = open(str(voice.file_id) + '.mp3', 'rb')
    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
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
    if run.status is not 'completed':
        await message.answer("Something went wrong. Please try again.")
        os.remove(str(voice.file_id) + '.mp3')
        return
    messages = await client.beta.threads.messages.list(
        thread_id=thread.id
    )
    response = messages.data[0].content[0].text.value
    await state.update_data(thread=thread)

    print("response="+response)

    audio_response = await client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=response,
    )
    with open(str(voice.file_id) + '.mp3', 'wb') as audio_file:
        audio_file.write(audio_response.read())
    audio_file = FSInputFile(str(voice.file_id) + '.mp3')
    await message.answer_voice(voice=audio_file)
    os.remove(str(voice.file_id) + '.mp3')


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
