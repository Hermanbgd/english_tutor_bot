import asyncio
import logging
import os
from contextlib import suppress

from aiogram import Bot, Router, F
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, ChatMemberUpdated, Message
from app.bot.enums.roles import UserRole
from app.bot.keyboards.menu_button import get_main_menu_commands
from app.bot.services.voice_to_text_service import transcribe_voice_message
from app.bot.services.ai_service import generate_ai_reply
from app.bot.states.states import LangSG
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

    # if await state.get_state() == LangSG.lang:
    #     data = await state.get_data()
    #     with suppress(TelegramBadRequest):
    #         msg_id = data.get("lang_settings_msg_id")
    #         if msg_id:
    #             await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=msg_id)
    #     user_lang = await get_user_lang(conn, user_id=message.from_user.id)
    #     i18n = translations.get(user_lang)

    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=message.from_user.id
        )
    )

    # await message.answer(text=i18n.get("/start"))
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


# Этот хэгдлер срабатывает на отправку боту голосового сообщения
@user_router.message(F.voice)
async def handle_voice(message: Message, conn: AsyncConnection):
    try:
        logger.info(f"Получено голосовое сообщение от пользователя {message.from_user.id}")
        user_mes = await transcribe_voice_message(message.bot, message.voice.file_id)
        ai_reply = await generate_ai_reply(conn, message.from_user.id, user_mes)
        await message.answer(f"Распознанный текст:\n{user_mes}")
        await message.answer(ai_reply)
    except Exception as e:
        logger.exception(f"Ошибка при обработке голосового сообщения: {e}")
        await message.reply("Произошла ошибка при обработке вашего голосового сообщения. Попробуйте ещё раз.")

