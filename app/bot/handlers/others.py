from aiogram import Router
from aiogram.types import Message
from psycopg import AsyncConnection

# Инициализируем роутер уровня модуля
others_router = Router()


# Этот хэндлер будет срабатывать на любые апдейты типа `Message`, которые не забрали
# хэндлеры из других роутеров
@others_router.message()
async def send_info_message(message: Message, conn: AsyncConnection) -> None:
    await message.reply(chat_id=message.chat.id, text="Извините, я не знаю, что на это ответить...")