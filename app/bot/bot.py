import asyncio
import logging

from aiohttp import web
from aiogram.types import Update

import psycopg_pool
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from app.bot.handlers.admin import admin_router
from app.bot.handlers.others import others_router
from app.bot.handlers.user import user_router
from app.bot.middlewares.database import DataBaseMiddleware
from app.bot.middlewares.shadow_ban import ShadowBanMiddleware
from app.bot.middlewares.throttle import ThrottleMiddleware
from app.infrastructure.database.connection import get_pg_pool
from config.config import Config
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main(config: Config) -> None:
    logger.info("Starting bot...")
    # Инициализируем хранилище
    storage = RedisStorage(
        redis=Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            username=config.redis.username,
        )
    )

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Создаём пул соединений с Postgres
    db_pool: psycopg_pool.AsyncConnectionPool = await get_pg_pool(
        db_name=config.db.name,
        host=config.db.host,
        port=config.db.port,
        user=config.db.user,
        password=config.db.password,
    )


    # Подключаем роутеры в нужном порядке
    logger.info("Including routers...")
    dp.include_routers(admin_router, user_router, others_router)

    # Подключаем миддлвари в нужном порядке
    logger.info("Including middlewares...")
    dp.update.middleware(DataBaseMiddleware())
    dp.update.middleware(ShadowBanMiddleware())
    dp.update.middleware(ThrottleMiddleware(max_messages=5, window_seconds=10))


    # Запускаем поллинг
    # try:
    #     await dp.start_polling(
    #         bot, db_pool=db_pool,
    #         admin_ids=config.bot.admin_ids
    #     )
    # except Exception as e:
    #     logger.exception(e)
    # finally:
    #     # Закрываем пул соединений
    #     await db_pool.close()
    #     logger.info("Connection to Postgres closed")

    # Настройка webhook
    WEBHOOK_PATH = f"/webhook/{config.bot.token}"
    WEBHOOK_URL = f"https://englishtutorbot.ru{WEBHOOK_PATH}"

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()

    async def handle_webhook(request):
        token = request.match_info.get('token')
        if token != config.bot.token:
            return web.Response(status=403)
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot=bot, update=update)
        return web.Response()

    app.router.add_post(f'/webhook/{{token}}', handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    logger.info(f"Webhook запущен: {WEBHOOK_URL}")
    logger.info("Бот работает на вебхуках, порт 8443")

    try:
        # Бесконечный цикл — держим сервер живым
        await asyncio.Event().wait()
    except Exception as e:
        logger.exception(e)
    finally:
        # При завершении удаляем webhook и закрываем соединения
        await bot.delete_webhook()
        await db_pool.close()
        logger.info("Webhook удалён, соединение с Postgres закрыто")
