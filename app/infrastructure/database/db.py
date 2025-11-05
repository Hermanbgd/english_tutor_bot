import logging
from datetime import datetime, timezone
from typing import Any, Optional

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


async def get_last_dialog_topic(conn: AsyncConnection, user_id: int) -> Optional[str]:
    """
    Возвращает тему последнего диалога пользователя, если в БД есть хранение темы.
    По умолчанию попробуем извлечь из последних пар (например, по эвристике) —
    здесь заглушка, возвращающая None, если отдельного поля темы нет.
    При наличии таблицы dialog_topics (user_id, topic, created_at) — используйте её.
    """
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT topic
                FROM dialog_topics
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
    except Exception:
        # Если таблицы нет — спокойно вернуть None, будет фолбэк на general conversation
        return None
    return None


async def reset_user_dialog_history(conn: AsyncConnection, user_id: int) -> None:
    """Удаляет всю историю диалога пользователя."""
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            DELETE FROM dialog_history
            WHERE user_id = %s
            """,
            (user_id,)
        )


async def save_dialog_topic(conn: AsyncConnection, user_id: int, topic: str) -> None:
    """Сохраняет тему диалога (append-only)."""
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO dialog_topics (user_id, topic, created_at)
            VALUES (%s, %s, NOW())
            """,
            (user_id, topic)
        )


async def save_error_explanation(
    conn: AsyncConnection,
    user_id: int,
    message_id: int,
    original_text: str,
    explanation_text: str
) -> None:
    async with conn.transaction():
        async with conn.cursor() as cursor:
            # Добавляем новую запись (или обновляем, если существует)
            await cursor.execute(
                """
                INSERT INTO error_explanations (user_id, message_id, original_text, explanation_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, message_id) DO UPDATE
                SET original_text = EXCLUDED.original_text,
                    explanation_text = EXCLUDED.explanation_text,
                    created_at = NOW()
                """,
                (user_id, message_id, original_text, explanation_text)
            )
            # Удаляем все, кроме 5 последних записей
            await cursor.execute(
                """
                DELETE FROM error_explanations
                WHERE user_id = %s
                AND message_id NOT IN (
                    SELECT message_id
                    FROM error_explanations
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                )
                """,
                (user_id, user_id)
            )

async def get_explanation_text(
    conn: AsyncConnection,
    user_id: int,
    message_id: int
) -> Optional[str]:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT explanation_text
            FROM error_explanations
            WHERE user_id = %s AND message_id = %s
            """,
            (user_id, message_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def get_original_text(
    conn: AsyncConnection,
    user_id: int,
    message_id: int
) -> Optional[str]:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT original_text
            FROM error_explanations
            WHERE user_id = %s AND message_id = %s
            """,
            (user_id, message_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_admin_statistics(conn: AsyncConnection) -> list[tuple[str, int]]:
    """Возвращает простую статистику для админов: количество пользователей, активных, забаненных, сообщений в диалогах, сохраненных тем."""
    results: list[tuple[str, int]] = []
    async with conn.cursor() as cursor:
        # Всего пользователей
        await cursor.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        results.append(("Всего пользователей", total_users))

        # Активные пользователи
        await cursor.execute("SELECT COUNT(*) FROM users WHERE is_alive = TRUE")
        alive_users = (await cursor.fetchone())[0]
        results.append(("Активных пользователей", alive_users))

        # Забаненные
        await cursor.execute("SELECT COUNT(*) FROM users WHERE banned = TRUE")
        banned_users = (await cursor.fetchone())[0]
        results.append(("Забаненных пользователей", banned_users))

        # Количество записей в истории диалога
        await cursor.execute("SELECT COUNT(*) FROM dialog_history")
        total_pairs = (await cursor.fetchone())[0]
        results.append(("Записей в истории диалогов", total_pairs))

        # Количество сохраненных тем
        await cursor.execute("SELECT COUNT(*) FROM dialog_topics")
        total_topics = (await cursor.fetchone())[0]
        results.append(("Сохраненных тем", total_topics))

    return results

