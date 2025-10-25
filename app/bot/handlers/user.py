import asyncio
import logging
import os
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from app.bot.enums.roles import UserRole
from app.bot.keyboards.menu_button import get_main_menu_commands
from app.bot.services.translation_service import translate_en_to_ru
from app.bot.services.voice_to_text_service import transcribe_voice_message
from app.bot.services.ai_service import generate_ai_reply
from app.bot.services.grammar_service import get_corrected_sentence
from app.bot.services.speech_service import t_t_v
from app.infrastructure.database.db import (
    add_user,
    change_user_alive_status,
    get_user,
)
from psycopg.connection_async import AsyncConnection

logger = logging.getLogger(__name__)

# Инициализируем роутер уровня модуля
user_router = Router()


# Этот хэндлер срабатывает на команду /start
@user_router.message(CommandStart())
async def process_start_command(
        message: Message,
        conn: AsyncConnection,
        bot: Bot,
        state: FSMContext,
        admin_ids: list[int]
):
    user_row = await get_user(conn, user_id=message.from_user.id)
    if user_row is None:
        if message.from_user.id in admin_ids:
            user_role = UserRole.ADMIN
        else:
            user_role = UserRole.USER

        await add_user(
            conn,
            user_id=message.from_user.id,
            username=message.from_user.username,
            role=user_role
        )
    else:
        user_role = UserRole(user_row[4])
        await change_user_alive_status(
            conn,
            is_alive=True,
            user_id=message.from_user.id,
        )

    await message.answer(text="Вы добавлены в базу данных, можете пользоваться ботом")
    await state.clear()


# Этот хэндлер срабатывает на команду /help
@user_router.message(Command(commands="help"))
async def process_help_command(message: Message, i18n: dict[str, str]):
    await message.answer(text=i18n.get("/help"))


# Этот хэндлер будет срабатывать на блокировку бота пользователем
@user_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def process_user_blocked_bot(event: ChatMemberUpdated, conn: AsyncConnection):
    logger.info("User %d has blocked the bot", event.from_user.id)
    await change_user_alive_status(conn, user_id=event.from_user.id, is_alive=False)


# Этот хэндлер срабатывает на отправку боту голосового сообщения
@user_router.message(F.voice)
async def handle_voice(message: Message, conn: AsyncConnection):
    ai_voice = None
    try:
        logger.info(f"Получено голосовое сообщение от пользователя {message.from_user.id}")
        user_mes = await transcribe_voice_message(message.bot, message.voice.file_id)
        logger.info(f"Преобразованное текстовое сообщение: {user_mes}")
         # Проверка грамматики
        corrected_sentence = await get_corrected_sentence(user_mes)
        if corrected_sentence != "No errors.":
            await message.answer(corrected_sentence, parse_mode=ParseMode.HTML)
            logger.info(f"Отправлено исправленное сообщение: {corrected_sentence}")
        # Генерация ответа ИИ
        ai_reply = await generate_ai_reply(conn, message.from_user.id, user_mes)
        logger.info(f"Получен ответ от модели {ai_reply}")
        ai_voice = await t_t_v(ai_reply)
        if ai_voice:
            voice = FSInputFile(ai_voice)
            await message.answer_voice(voice)
            logger.info(f"Голосовое сообщение: '{ai_reply}' отправлено")

            # отправка скрытых сообщений
            answer_ai_spoiler = f'<span class="tg-spoiler">{ai_reply}</span>'
            await message.answer(text=f'Текст:  {answer_ai_spoiler}', parse_mode=ParseMode.HTML)

            translate_ai_answer = await translate_en_to_ru(ai_reply)
            answer_ru_ai_spoiler = f'<span class="tg-spoiler">{translate_ai_answer}</span>'
            await message.answer(text=f'Перевод:  {answer_ru_ai_spoiler}', parse_mode=ParseMode.HTML)
        else:
            await message.answer(ai_reply)
            logger.info(f"Не получилось озвучить сообщение: '{ai_reply}' отправлен текст")
            # отправка скрытого перевода
            translate_ai_answer = await translate_en_to_ru(ai_reply)
            answer_ru_ai_spoiler = f'<span class="tg-spoiler">{translate_ai_answer}</span>'
            await message.answer(text=f'Перевод:  {answer_ru_ai_spoiler}', parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception(f"Ошибка при обработке голосового сообщения: {e}")
        await message.reply("Произошла ошибка при обработке вашего голосового сообщения. Попробуйте ещё раз.")
    finally:
        if ai_voice and os.path.exists(ai_voice):
            os.remove(ai_voice)
            logger.info(f"Deleted voice file: {ai_voice}")

