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
                            language VARCHAR(10) NOT NULL,
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
                logger.info("Tables `users` and `dialog_history` were successfully created")
    except Error as db_error:
        logger.exception("Database-specific error: %s", db_error)
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
    finally:
        if connection:
            await connection.close()
            logger.info("Connection to Postgres closed")

asyncio.run(main())
