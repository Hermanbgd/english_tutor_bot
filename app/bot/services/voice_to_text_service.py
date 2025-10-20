import os
import sys
import asyncio
import logging
from pydub import AudioSegment
import whisper
from aiogram import Bot

logger = logging.getLogger(__name__)

# Настройка цикла событий для Windows
if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Загружаем модель один раз при импорте
try:
    model = whisper.load_model("base")
    logger.info("Whisper model loaded successfully.")
except Exception as e:
    logger.exception("Failed to load Whisper model: %s", e)
    raise

def ogg_to_wav(ogg_path, wav_path):
    try:
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio.export(wav_path, format="wav")
        logger.info(f"Converted {ogg_path} to {wav_path}")
    except Exception as e:
        logger.exception(f"Failed to convert {ogg_path} to {wav_path}: {e}")
        raise

async def transcribe_voice_message(bot: Bot, file_id: str) -> str:
    ogg_path = wav_path = None
    try:
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path

        ogg_path = f"{file_id}.ogg"
        await bot.download_file(file_path, destination=ogg_path)
        logger.info(f"Downloaded file: {ogg_path}")

        loop = asyncio.get_running_loop()
        wav_path = ogg_path.replace('.ogg', '.wav')
        await loop.run_in_executor(None, ogg_to_wav, ogg_path, wav_path)

        result = await loop.run_in_executor(
            None, lambda: model.transcribe(wav_path, language="en")
        )
        text = result["text"]
        logger.info(f"Transcribed text: {text}")
        return text
    except Exception as e:
        logger.exception(f"Error transcribing voice message: {e}")
        raise  # или вернуть сообщение об ошибке, например, "Failed to transcribe"
    finally:
        for path in (ogg_path, wav_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Deleted temp file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {path}: {e}")