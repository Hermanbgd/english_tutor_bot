# Для запуска миграций из контейнера, когда в постгрес и редис хосты указаны по названию:
# docker-compose exec bot python -m migrations.create_tables
# Добавил в докерфайл строку для запуска сначала миграций, автоматически. Сейчас не нужно отдельно
# docker compose build bot
# docker compose up -d bot
import asyncio
import logging
import os
import sys

from app.infrastructure.database.connection import get_pg_connection
from config.config import Config, load_config
from psycopg import AsyncConnection, Error

config: Config = load_config()

logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger = logging.getLogger(__name__)

# Настройка цикла событий для Windows
if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    connection: AsyncConnection | None = None

    try:
        connection = await get_pg_connection(
            db_name=config.db.name,
            host=config.db.host,
            port=config.db.port,
            user=config.db.user,
            password=config.db.password,
        )
        async with connection:
            async with connection.transaction():
                async with connection.cursor() as cursor:
                    # Таблица пользователей
                    await cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users(
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL UNIQUE,
                            username VARCHAR(50),
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            role VARCHAR(30) NOT NULL,
                            is_alive BOOLEAN NOT NULL,
                            banned BOOLEAN NOT NULL
                        );
                        """
                    )
                    # Таблица истории диалога
                    await cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS dialog_history(
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                            user_message TEXT NOT NULL,
                            ai_message TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        CREATE INDEX IF NOT EXISTS idx_dialog_history_user_time
                        ON dialog_history (user_id, created_at DESC);
                        """
                    )
                    # таблица для разборов ошибок
                    await cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS error_explanations(
                        user_id BIGINT NOT NULL,
                        message_id BIGINT NOT NULL,
                        original_text TEXT NOT NULL,
                        explanation_text TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (user_id, message_id),
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                        );
                        CREATE INDEX IF NOT EXISTS idx_error_explanations_user_message
                        ON error_explanations (user_id, message_id);
                        CREATE INDEX IF NOT EXISTS idx_error_explanations_user_time
                        ON error_explanations (user_id, created_at DESC);
                        """
                    )
                logger.info("Tables `users`, `dialog_history`, `error_explanations` were successfully created")
    except Error as db_error:
        logger.exception("Database-specific error: %s", db_error)
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
    finally:
        if connection:
            await connection.close()
            logger.info("Connection to Postgres closed")

asyncio.run(main())
