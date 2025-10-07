from groq import Groq
import tiktoken
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация токенизатора один раз при старте
encoding = tiktoken.get_encoding("cl100k_base")

# Инициализация Groq
client = Groq(api_key="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")

# Системный промпт
system_prompt = {
    "role": "system",
    "content": "You're a friendly, casual assistant. Answer in a max of 3 sentences, in a conversational tone. Occasionally ask a short follow-up question, but not always."
}

# История сообщений
history = [system_prompt]

# Максимум 5 пар (10 сообщений + system)
MAX_MESSAGES = 11

# Подсчёт токенов в истории
def count_tokens(messages):
    total_tokens = 0
    for msg in messages:
        total_tokens += len(encoding.encode(msg["content"]))
    return total_tokens

# Обрезка текста до ~20 токенов
def trim_message(text, max_tokens=20):
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        return encoding.decode(tokens[:max_tokens]) + "..."
    return text

# Обрезка истории
def trim_history():
    if len(history) > MAX_MESSAGES:
        history[:] = [system_prompt] + history[-10:]  # Последние 10
    # Обрезаем каждое сообщение до ~20 токенов
    for msg in history[1:]:  # Пропускаем system prompt
        msg["content"] = trim_message(msg["content"])
    logger.info(f"Total tokens in history: {count_tokens(history)}")
    logger.debug(f"Current history: {history}")

async def handle_message(user_input: str) -> str:
    if not user_input:
        logger.warning("Received empty user input")
        return "Похоже, вы ничего не написали!"

    # Добавляем сообщение пользователя
    history.append({"role": "user", "content": user_input})
    trim_history()

    try:
        # Отправляем запрос
        chat_completion = client.chat.completions.create(
            messages=history,
            model="llama-3.3-70b-versatile",
            max_tokens=100,
            temperature=0.8,
        )
        response = chat_completion.choices[0].message.content
        logger.info(f"Generated response: {response}")

        # Добавляем ответ модели
        history.append({"role": "assistant", "content": response})
        trim_history()

        return response
    except Exception as e:
        logger.error(f"Error during chat completion: {str(e)}")
        return "Упс, что-то пошло не так! Попробуйте ещё раз."