import sys
import tempfile
import os
from gtts import gTTS
import asyncio
import logging

logger = logging.getLogger(__name__)

# Настройка цикла событий для Windows
if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def t_t_v(text):
    try:
        tts = gTTS(text, lang='en', tld="com")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_name = tmp.name
        tts.save(temp_name)
        logger.info(f"Generated and save audio file: {temp_name}")
        return temp_name
    except Exception as e:
        logger.exception(f"Error in t_t_v function: {e}")
        raise
