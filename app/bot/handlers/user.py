import asyncio
import logging
import os
from contextlib import suppress

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.types import ChatMemberUpdated, Message
from app.bot.enums.roles import UserRole
from app.bot.keyboards.keyboards import error_analysis_keyboard, hide_keyboard, ERROR_BTN, HIDE_BTN
from app.bot.services.translation_service import translate_en_to_ru
from app.bot.services.voice_to_text_service import transcribe_voice_message
from app.bot.services.ai_service import generate_ai_reply
from app.bot.services.grammar_service import get_corrected_sentence, get_error_explanation
from app.bot.services.speech_service import t_t_v
from app.infrastructure.database.db import (
    add_user,
    change_user_alive_status,
    get_user,
    save_error_explanation,
    get_original_text,
    get_explanation_text
)
from psycopg.connection_async import AsyncConnection

logger = logging.getLogger(__name__)

# Инициализируем роутер уровня модуля
user_router = Router()


@user_router.callback_query(F.data == ERROR_BTN)
async def on_show_analysis(callback: Message, conn: AsyncConnection):
    # Only respond if this message exists in last 5 entries; db getters will return None otherwise
    explanation = await get_explanation_text(conn, user_id=callback.from_user.id, message_id=callback.message.message_id)
    if explanation is None:
        # silently ignore by answering callback, no edit
        with suppress(Exception):
            await callback.answer()
        return
    try:
        await callback.message.edit_text(explanation)
        await callback.message.edit_reply_markup(reply_markup=hide_keyboard())
    except TelegramBadRequest:
        pass
    finally:
        with suppress(Exception):
            await callback.answer()


@user_router.callback_query(F.data == HIDE_BTN)
async def on_hide_analysis(callback: Message, conn: AsyncConnection):
    original = await get_original_text(conn, user_id=callback.from_user.id, message_id=callback.message.message_id)
    if original is None:
        with suppress(Exception):
            await callback.answer()
        return
    try:
        await callback.message.edit_text(original, parse_mode=ParseMode.HTML)
        await callback.message.edit_reply_markup(reply_markup=error_analysis_keyboard())
    except TelegramBadRequest:
        pass
    finally:
        with suppress(Exception):
            await callback.answer()


# Этот хэндлер срабатывает на команду /start
@user_router.message(CommandStart())
async def process_start_command(
        message: Message,
        conn: AsyncConnection,
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
        # user_row: (id, user_id, username, role, is_alive, banned, created_at)
        # Валидируем значение роли, но не сохраняем переменную
        _ = UserRole(user_row[3])
        await change_user_alive_status(
            conn,
            is_alive=True,
            user_id=message.from_user.id,
        )

    await state.clear()
    await message.answer(text="Диалог запущен. Отправьте голосовое сообщение для начала общения.")


# Этот хэндлер срабатывает на команду /help
@user_router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(text=(
        "Доступные команды:\n"
        "/start — старт диалога\n"
        "/restart — перезапустить диалог\n"
        "/continue — продолжить диалог\n"
        "/pause — пауза диалога\n"
        "/stop — стоп диалога\n"
        "/newwords — 5 новых слов по теме\n"
        "/help — помощь"
    ))


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
        # отправляем временное сообщение
        sent_trans = await message.answer("Распознаю голосовое сообщение...")

        # Преобразование голосового сообщения в текст
        logger.info(f"Получено голосовое сообщение от пользователя {message.from_user.id}")
        user_mes = await transcribe_voice_message(message.bot, message.voice.file_id)
        logger.info(f"Преобразованное текстовое сообщение: {user_mes}")

        # Удаляем временное сообщение
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_trans.message_id)
        except Exception as del_err:
            logger.warning(f"Ошибка при удалении временного сообщения: {del_err}")

        # Информируем пользователя, что бот обрабатывает сообщение
        await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')

         # Проверка грамматики
        corrected_sentence = await get_corrected_sentence(user_mes)

        if corrected_sentence != "No errors.":
            err_expl = await get_error_explanation(user_mes, corrected_sentence[1])

        # Если есть исправления, отправляем исправленный текст и сохраняем объяснение
            # Сначала отправляем исправленный текст и получаем его message_id
            sent = await message.answer(
                corrected_sentence[0],
                parse_mode=ParseMode.HTML,
                reply_markup=error_analysis_keyboard()
            )
            # Сохраняем запись, привязавшись к message_id сообщения бота
            await save_error_explanation(
                conn,
                user_id=message.from_user.id,
                message_id=sent.message_id,
                original_text=corrected_sentence[0],
                explanation_text=err_expl
            )
            logger.info(f"Сохранено оригинальное сообщение и его объяснение: {corrected_sentence[0]}, {err_expl}")
            logger.info(f"Отправлено исправленное сообщение: {corrected_sentence[0]}")

        # Информируем пользователя, что бот генерирует голосовое
        await message.bot.send_chat_action(chat_id=message.chat.id, action='record_voice')

        # Генерация ответа ИИ
        ai_reply = await generate_ai_reply(conn, message.from_user.id, user_mes)
        logger.info(f"Получен ответ от модели {ai_reply}")

        # Перед озвучиванием: отправляем временное сообщение
        sent_voice = await message.answer("Озвучиваю ответ...")

        # Генерация голоса
        ai_voice = await t_t_v(ai_reply)

        # Удаляем временное сообщение
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_voice.message_id)
        except Exception as del_err:
            logger.warning(f"Ошибка при удалении временного сообщения: {del_err}")

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

