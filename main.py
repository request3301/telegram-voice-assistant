import asyncio
import logging
import sys
from os import getenv

from openai import AsyncOpenAI

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

client = AsyncOpenAI()

bot = Bot(token=getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
    msg = await client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=transcription.text,
    )
    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
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


async def main() -> None:
    global assistant
    assistant = await client.beta.assistants.create(model="gpt-4o")
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
