import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from app.bot.enums.roles import UserRole
from app.bot.filters.filters import UserRoleFilter
from app.infrastructure.database.db import (
    change_user_banned_status_by_id,
    change_user_banned_status_by_username,
    get_user_banned_status_by_id,
    get_user_banned_status_by_username,
)
from psycopg import AsyncConnection

logger = logging.getLogger(__name__)

admin_router = Router()

admin_router.message.filter(UserRoleFilter(UserRole.ADMIN))


# Этот хэндлер будет срабатывать на команду /help для пользователя с ролью `UserRole.ADMIN`
@admin_router.message(Command('help'))
async def process_admin_help_command(message: Message):
    await message.answer(text=(
        "Доступные команды для администратора:\n"
        "/ban <user_id|@username> — забанить пользователя\n"
        "/unban <user_id|@username> — разбанить пользователя\n"
        "/statistics — посмотреть статистику"
    ))


# Этот хэндлер будет срабатывать на команду /statistics для пользователя с ролью `UserRole.ADMIN`
@admin_router.message(Command('statistics'))
async def process_admin_statistics_command(message: Message, conn: AsyncConnection):
    from app.infrastructure.database.db import get_admin_statistics
    stats = await get_admin_statistics(conn)
    if not stats:
        await message.answer("Статистика пока недоступна.")
        return
    lines = []
    for i, (name, value) in enumerate(stats, 1):
        lines.append(f"{i}. {name}: {value}")
    await message.answer("Статистика:\n" + "\n".join(lines))


# Этот хэндлер будет срабатывать на команду /ban для пользователя с ролью `UserRole.ADMIN`
@admin_router.message(Command("ban"))
async def process_ban_command(
        message: Message,
        command: CommandObject,
        conn: AsyncConnection,
) -> None:
    args = command.args

    if not args:
        await message.reply("Укажите user_id или @username: /ban <user_id|@username>")
        return

    arg_user = args.split()[0].strip()

    if arg_user.isdigit():
        banned_status = await get_user_banned_status_by_id(conn, user_id=int(arg_user))
    elif arg_user.startswith('@'):
        banned_status = await get_user_banned_status_by_username(conn, username=arg_user[1:])
    else:
        await message.reply(text="Неверный аргумент. Используйте: /ban <user_id|@username>")
        return

    if banned_status is None:
        await message.reply("Пользователь не найден.")
    elif banned_status:
        await message.reply("Пользователь уже забанен.")
    else:
        if arg_user.isdigit():
            await change_user_banned_status_by_id(conn, user_id=int(arg_user), banned=True)
        else:
            await change_user_banned_status_by_username(conn, username=arg_user[1:], banned=True)
        await message.reply(text="Пользователь забанен.")


# Этот хэндлер будет срабатывать на команду /unban для пользователя с ролью `UserRole.ADMIN`
@admin_router.message(Command('unban'))
async def process_unban_command(
        message: Message,
        command: CommandObject,
        conn: AsyncConnection,
) -> None:
    args = command.args

    if not args:
        await message.reply("Укажите user_id или @username: /unban <user_id|@username>")
        return

    arg_user = args.split()[0].strip()

    if arg_user.isdigit():
        banned_status = await get_user_banned_status_by_id(conn, user_id=int(arg_user))
    elif arg_user.startswith('@'):
        banned_status = await get_user_banned_status_by_username(conn, username=arg_user[1:])
    else:
        await message.reply(text="Неверный аргумент. Используйте: /unban <user_id|@username>")
        return

    if banned_status is None:
        await message.reply("Пользователь не найден.")
    elif banned_status:
        if arg_user.isdigit():
            await change_user_banned_status_by_id(conn, user_id=int(arg_user), banned=False)
        else:
            await change_user_banned_status_by_username(conn, username=arg_user[1:], banned=False)
        await message.reply(text="Пользователь разбанен.")
    else:
        await message.reply("Пользователь не забанен.")