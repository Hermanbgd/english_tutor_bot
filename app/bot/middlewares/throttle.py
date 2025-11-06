import time
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, User

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """
    Простая троттлинг-мидлварь: ограничивает частоту сообщений от пользователя.
    Параметры по умолчанию: max_messages=5 за window_seconds=10 секунд.
    Если лимит превышен, событие игнорируется (не передается в хэндлеры).
    """

    def __init__(self, max_messages: int = 5, window_seconds: int = 10) -> None:
        super().__init__()
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._buckets: Dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user: User = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        bucket = self._buckets.setdefault(user.id, [])
        # Удаляем записи старше окна
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        # Фиксируем текущее событие
        bucket.append(now)

        if len(bucket) > self.max_messages:
            # Превышение лимита — игнорируем событие
            logger.warning("User %d throttled: %d msgs in %ds", user.id, len(bucket), self.window_seconds)
            # Не отвечаем, просто не пропускаем дальше
            return

        return await handler(event, data)
