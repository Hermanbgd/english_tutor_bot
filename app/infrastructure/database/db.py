import logging
from datetime import datetime, timezone
from typing import Any

from app.bot.enums.roles import UserRole
from psycopg import AsyncConnection

logger = logging.getLogger(__name__)


async def add_user(
    conn: AsyncConnection,
    *,
    user_id: int,
    username: str | None = None,
    role: UserRole = UserRole.USER,
    is_alive: bool = True,
    banned: bool = False,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                INSERT INTO users(user_id, username, role, is_alive, banned)
                VALUES(
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s
                ) ON CONFLICT (user_id) DO NOTHING;
            """,
            (
                user_id,
                username,
                role,
                is_alive,
                banned,
            ),
        )
    logger.info(
        "User added. Table=`%s`, user_id=%d, created_at='%s', "
        "role=%s, is_alive=%s, banned=%s",
        "users",
        user_id,
        datetime.now(timezone.utc),
        role,
        is_alive,
        banned,
    )


async def get_user(
    conn: AsyncConnection,
    *,
    user_id: int,
) -> tuple[Any, ...] | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                SELECT 
                    id,
                    user_id,
                    username,
                    role,
                    is_alive,
                    banned,
                    created_at
                    FROM users WHERE user_id = %s;
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
    logger.info("Row is %s", row)
    return row if row else None


async def change_user_alive_status(
    conn: AsyncConnection,
    *,
    is_alive: bool,
    user_id: int,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                UPDATE users
                SET is_alive = %s
                WHERE user_id = %s;
            """,
            (is_alive, user_id)
        )
    logger.info("Updated `is_alive` status to `%s` for user %d", is_alive, user_id)


async def change_user_banned_status_by_id(
    conn: AsyncConnection,
    *,
    banned: bool,
    user_id: int,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                UPDATE users
                SET banned = %s
                WHERE user_id = %s
            """,
            (banned, user_id)
        )
    logger.info("Updated `banned` status to `%s` for user %d", banned, user_id)


async def change_user_banned_status_by_username(
    conn: AsyncConnection,
    *,
    banned: bool,
    username: str,
) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                UPDATE users
                SET banned = %s
                WHERE username = %s
            """,
            (banned, username)
        )
    logger.info("Updated `banned` status to `%s` for username %s", banned, username)


async def get_user_alive_status(
    conn: AsyncConnection,
    *,
    user_id: int,
) -> bool | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                SELECT is_alive FROM users WHERE user_id = %s;
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
    if row:
        logger.info("The user with `user_id`=%s has the is_alive status is %s", user_id, row[0])
    else:
        logger.warning("No user with `user_id`=%s found in the database", user_id)
    return row[0] if row else None


async def get_user_banned_status_by_id(
    conn: AsyncConnection,
    *,
    user_id: int,
) -> bool | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                SELECT banned FROM users WHERE user_id = %s;
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
    if row:
        logger.info("The user with `user_id`=%s has the banned status is %s", user_id, row[0])
    else:
        logger.warning("No user with `user_id`=%s found in the database", user_id)
    return row[0] if row else None


async def get_user_banned_status_by_username(
    conn: AsyncConnection,
    *,
    username: str,
) -> bool | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                SELECT banned FROM users WHERE username = %s;
            """,
            (username,),
        )
        row = await cursor.fetchone()
    if row:
        logger.info("The user with `username`=%s has the banned status is %s", username, row[0])
    else:
        logger.warning("No user with `username`=%s found in the database", username)
    return row[0] if row else None


async def get_user_role(
    conn: AsyncConnection,
    *,
    user_id: int,
) -> UserRole | None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
                SELECT role FROM users WHERE user_id = %s;
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
    if row:
        logger.info("The user with `user_id`=%s has the role is %s", user_id, row[0])
        return UserRole(row[0])
    else:
        logger.warning("No user with `user_id`=%s found in the database", user_id)
    return None


async def save_dialog_pair(conn: AsyncConnection, user_id: int, user_message: str, ai_message: str) -> None:
    async with conn.transaction():
        async with conn.cursor() as cursor:
            # Добавляем новую пару
            await cursor.execute(
                """
                INSERT INTO dialog_history (user_id, user_message, ai_message)
                VALUES (%s, %s, %s)
                """,
                (user_id, user_message, ai_message)
            )
            # Удаляем все, кроме 5 последних пар
            await cursor.execute(
                """
                DELETE FROM dialog_history
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM dialog_history
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 5
                    ) AS t
                ) AND user_id = %s
                """,
                (user_id, user_id)
            )


async def get_last_5_pairs(conn: AsyncConnection, user_id: int) -> list[tuple[Any, ...]]:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT user_message, ai_message
            FROM dialog_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
    # Разворачиваем, чтобы пары шли от старых к новым
    return list(reversed(rows)) if rows else []

#
#
# Как сформировать словарь для отправки в AI
# Допустим, вы хотите получить список словарей такого вида:
# [
#     {"user": "Hi!", "ai": "Hello!"},
#     {"user": "How are you?", "ai": "I'm fine, thanks!"},
#     ...
# ]
#
#
# pairs = await get_last_10_pairs(connection, user_id)
# dialog = [{"user": row["user_message"], "ai": row["ai_message"]} for row in pairs]
#
# async def build_dialog(connection, user_id):
#     pairs = await get_last_10_pairs(connection, user_id)
#     dialog = [{"user": row["user_message"], "ai": row["ai_message"]} for row in pairs]
#     return dialog
#
# async def main():
#     # ... тут подключение к БД ...
#     dialog = await build_dialog(connection, user_id)
#     # ... используете dialog дальше ...
#
# # Запуск
# import asyncio
# asyncio.run(main())

