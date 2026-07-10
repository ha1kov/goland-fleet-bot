from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import settings
from db.models import init_db
from handlers import common, edit, search, add
from scheduler.notifications import build_scheduler
from utils.importer import import_xlsx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DbPathMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["db_path"] = settings.db_path
        return await handler(event, data)


BOT_COMMANDS = [
    BotCommand(command="start",  description="Головне меню"),
    BotCommand(command="help",   description="Допомога та інструкції"),
    BotCommand(command="search", description="Пошук авто за номером"),
    BotCommand(command="add",    description="Додати нове авто"),
    BotCommand(command="alerts", description="Перевірити прострочені ТО"),
]


async def main() -> None:
    logger.info("Initialising database at %s", settings.db_path)
    init_db(settings.db_path)

    import_xlsx(settings.xlsx_path, settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(DbPathMiddleware())
    dp.callback_query.middleware(DbPathMiddleware())

    dp.include_router(common.router)
    dp.include_router(add.router)
    dp.include_router(edit.router)
    dp.include_router(search.router)

    loop = asyncio.get_event_loop()
    scheduler = build_scheduler(
        bot=bot,
        admin_chat_id=settings.admin_chat_id,
        db_path=settings.db_path,
        warn_days=settings.to_warn_days,
        notify_hour=settings.notify_hour,
        notify_minute=settings.notify_minute,
        loop=loop,
    )
    scheduler.start()
    logger.info("Scheduler started.")

    await bot.set_my_commands(BOT_COMMANDS)

    logger.info("Bot is running. Polling for updates…")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
