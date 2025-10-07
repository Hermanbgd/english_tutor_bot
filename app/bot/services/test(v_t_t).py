import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from pydub import AudioSegment
import whisper

BOT_TOKEN = '8283291283:AAHfCfGq0lt98GP4RXJPt2lXDjhJo3xhiIw'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загружаем модель whisper один раз при запуске
try:
    logger.info("Загрузка модели Whisper...")
    model = whisper.load_model("base")
    logger.info("Модель Whisper успешно загружена.")
except Exception as e:
    logger.exception("Ошибка при загрузке модели Whisper: %s", e)
    raise

# Функция для конвертации временно скаченного аудио из формата ogg в формат wav
def ogg_to_wav(ogg_path, wav_path):
    try:
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio.export(wav_path, format="wav")
        logger.info(f"Конвертация {ogg_path} в {wav_path} завершена.")
    except Exception as e:
        logger.exception(f"Ошибка при конвертации {ogg_path} в {wav_path}: {e}")
        raise

@dp.message(F.voice)
async def handle_voice(message: Message):
    ogg_path = wav_path = None
    try:
        logger.info(f"Получено голосовое сообщение от пользователя {message.from_user.id}")

        # Получаем file_id и file_path
        voice = message.voice
        file_id = voice.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path

        ogg_path = f"{file_id}.ogg"
        # Скачиваем файл по file_path
        await bot.download_file(file_path, destination=ogg_path)
        logger.info(f"Файл сохранён: {ogg_path}")

        # Конвертация и распознавание — как раньше
        loop = asyncio.get_running_loop()
        wav_path = ogg_path.replace('.ogg', '.wav')
        await loop.run_in_executor(None, ogg_to_wav, ogg_path, wav_path)

        result = await loop.run_in_executor(
            None, lambda: model.transcribe(wav_path)
        )
        text = result["text"]
        logger.info(f"Распознанный текст: {text}")

        await message.reply(f"Распознанный текст:\n{text}")

    except Exception as e:
        logger.exception(f"Ошибка при обработке голосового сообщения: {e}")
        await message.reply("Произошла ошибка при обработке вашего голосового сообщения. Попробуйте ещё раз.")
    finally:
        for path in (ogg_path, wav_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Временный файл удалён: {path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {path}: {e}")


async def main():
    logger.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
