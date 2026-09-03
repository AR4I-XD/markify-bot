"""Главная точка входа Telegram-бота Markify."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src.config import settings
from src.database.db import db
from src.handlers.common import router as common_router
from src.handlers.image import router as image_router
from src.handlers.settings import router as settings_router


async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает подсказки команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="Главное меню и статус"),
        BotCommand(command="settings", description="Настройки логотипа и цветокоррекции"),
        BotCommand(command="help", description="Инструкция и возможности"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger("markify")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "placeholder_token":
        logger.error(
            "BOT_TOKEN не задан! Пожалуйста, укажите токен в файле .env (см. .env.example)"
        )
        return

    # Инициализация базы данных и каталогов
    await db.init()
    logger.info("База данных и хранилище успешно инициализированы.")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(settings_router)
    dp.include_router(image_router)

    await set_bot_commands(bot)
    logger.info("Markify Bot успешно запущен и ожидает сообщений...")

    try:
        # Сброс накопившихся апдейтов и старт поллинга
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
