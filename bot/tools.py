import os
from uuid import uuid4

from aiogram import Bot, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from environment import Settings
from llm.client import client

bot = Bot(token=Settings().TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

router = Router(name=__name__)


async def download_voice_as_text(voice) -> str:
    filepath = str(uuid4()) + ".mp3"
    await bot.download(voice, filepath)
    audio_file = open(filepath, 'rb')
    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    audio_file.close()
    os.remove(filepath)
    print(transcription)
    return transcription.text


async def send_voice(text: str, chat_id: int):
    print(f"Sending audio:\n{text}")

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


async def get_thread_id(state: FSMContext) -> int:
    data = await state.get_data()
    if 'thread_id' in data:
        return data['thread_id']
    thread = await client.beta.threads.create()
    await state.update_data(thread_id=thread.id)
    return thread.id
