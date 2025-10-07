import os
import sys
import asyncio
import logging
from typing import List, Dict
from config.config import Config, load_config
from groq import Groq
import tiktoken
from app.infrastructure.database.db import get_last_5_pairs, save_dialog_pair

config: Config = load_config()

logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger = logging.getLogger(__name__)

# Настройка цикла событий для Windows
if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Инициализация токенизатора один раз при импорте
try:
    encoding = tiktoken.get_encoding("cl100k_base")
    logger.info("tiktoken encoding loaded successfully.")
except Exception as e:
    logger.exception("Failed to initialize tiktoken encoding: %s", e)
    raise

# Инициализация Groq клиента один раз при импорте
try:
    client = Groq(api_key=config.grok.token)
    logger.info("Groq client initialized successfully.")
except Exception as e:
    logger.exception("Failed to initialize Groq client: %s", e)
    raise

# Системный промпт
system_prompt: Dict[str, str] = {
    "role": "system",
    "content": (
        "You're a friendly, casual assistant. Answer in a max of 3 sentences, in a conversational tone. "
        "Occasionally ask a short follow-up question, but not always."
    ),
}

# Обрезка сообщений до 20 токенов
def trim_message(text: str, max_tokens: int = 20) -> str:
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        return encoding.decode(tokens[:max_tokens]) + "..."
    return text


async def _build_messages_from_db(conn, user_id: int) -> List[Dict[str, str]]:
    """
    Построить список сообщений для модели на основе последних 5 пар из БД.
    Старые сообщения НЕ обрезаются повторно. Обрезка применяется только к новой паре.
    """
    messages: List[Dict[str, str]] = [system_prompt]

    # Получаем последние 5 пар из БД в порядке от старых к новым
    pairs = await get_last_5_pairs(conn, user_id)
    for user_msg, ai_msg in pairs:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": ai_msg})

    return messages


async def generate_ai_reply(conn, user_id: int, user_input: str) -> str:
    """
    Сгенерировать ответ Groq для пользователя user_id с учётом его истории из БД.

    Контекст: [system_prompt] + последние 5 пар из БД + новая пользовательская реплика (БЕЗ обрезки).
    После получения ответа модели выводим полный ответ в консоль, затем обрезаем новую пару
    и сохраняем её в БД (чтобы не обрезать повторно в будущем). Исторические пары берутся из БД как есть.
    Политика хранения последних 5 пар управляется БД.
    """
    if not user_input:
        logger.warning("Received empty user input")
        return "Похоже, вы ничего не написали!"

    # История из БД (без обрезки старых сообщений)
    messages = await _build_messages_from_db(conn, user_id)

    # Добавляем новую пользовательскую реплику (БЕЗ обрезки в контексте)
    messages.append({"role": "user", "content": user_input})

    try:
        loop = asyncio.get_running_loop()
        chat_completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                messages=messages,
                model=config.grok.model_dialog,
                max_tokens=100,
                temperature=0.8,
            ),
        )
        ai_response = chat_completion.choices[0].message.content
        logger.info("Generated response: %s", ai_response)

        # Обрезаем новую пару и сохраняем в БД, чтобы не обрезать повторно в будущем
        trimmed_user_input = trim_message(user_input)
        trimmed_ai_response = trim_message(ai_response)
        await save_dialog_pair(conn, user_id=user_id, user_message=trimmed_user_input, ai_message=trimmed_ai_response)

        return ai_response
    except Exception as e:
        logger.error("Error during chat completion: %s", e)
        return "Упс, что-то пошло не так! Попробуйте ещё раз."