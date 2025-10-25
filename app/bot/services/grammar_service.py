from config.config import Config, load_config
import aiohttp
import asyncio
from typing import List, Dict

config: Config = load_config()

URL = "https://app.chipp.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {config.ai.token}",
    "Content-Type": "application/json"
}


# === Функция для создания исправленного сообщения с зачеркнутым текстом ===
def combine_sentences(original: str, corrected: str) -> str:
    """
    Объединяет оригинал и исправление: удалённые слова — зачёркнуты <s>...</s>,
    добавленные — просто вставлены.
    """
    original_words = original.split()
    corrected_words = corrected.split()

    result = []
    i = 0  # индекс в original
    j = 0  # индекс в corrected

    while j < len(corrected_words):
        if i < len(original_words) and original_words[i] == corrected_words[j]:
            # Совпадение — просто добавляем
            result.append(corrected_words[j])
            i += 1
            j += 1
        else:
            # Слово в corrected новое — добавляем
            result.append(corrected_words[j])
            j += 1

            # Если есть "лишнее" слово в original — зачёркиваем
            if i < len(original_words) and (j >= len(corrected_words) or original_words[i] != corrected_words[j]):
                result.append(f"<s>{original_words[i]}</s>")
                i += 1

    # Добавляем оставшиеся слова из original как удалённые
    while i < len(original_words):
        result.append(f"<s>{original_words[i]}</s>")
        i += 1

    return " ".join(result)


# === Асинхронная функция проверки грамматики ===
async def get_corrected_sentence(user_input: str) -> str:
    """
    Проверяет грамматику, возвращает:
    - Исправленное предложение с <s>зачёркиванием</s> (если были ошибки)
    - "No errors." (если всё верно)
    - Сообщение об ошибке (если API упал)
    """
    if not user_input.strip():
        return "Пустой ввод."

    # Системный промпт
    SYSTEM_PROMPT: Dict[str, str] = {
        "role": "user",
        "content": (
            "You are an English grammar corrector. Output ONLY:\n"
            "- Corrected sentence if errors exist (no quotes/explanations).\n"
            "- 'No errors.' if correct.\n"
            "Ex:\n"
            "Input: what she is doing\n"
            "Output: What is she doing?\n"
            "Ex:\n"
            "Input: She is reading a book.\n"
            "Output: No errors.\n"
            f"Check: {user_input}"
        ),
    }

    messages: List[Dict[str, str]] = [SYSTEM_PROMPT.copy()]

    payload = {
        "model": "newapplication-61123",
        "messages": messages,
        "stream": False
    }

    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.post(URL, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0] \
                                     .get("message", {}) \
                                     .get("content", "").strip()

                    if content == "No errors.":
                        return "No errors."  # Всё верно
                    else:
                        # Есть исправление — применяем визуальную разницу
                        return combine_sentences(user_input, content)
                else:
                    error_text = await response.text()
                    print(f"API Error {response.status}: {error_text}")
                    return "Ошибка сервера."

    except asyncio.TimeoutError:
        return "Время ожидания истекло."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Произошла ошибка."
