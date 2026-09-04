"""Главная точка входа Telegram-бота Markify."""

import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src.config import settings
from src.database.db import db
from src.handlers.common import router as common_router
from src.handlers.image import router as image_router
from src.handlers.settings import router as settings_router
from src.middlewares.album import AlbumMiddleware


async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает подсказки команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="Главное меню и статус"),
        BotCommand(command="settings", description="Настройки логотипа и цветокоррекции"),
        BotCommand(command="help", description="Инструкция и возможности"),
    ]
    await bot.set_my_commands(commands)


async def health_handler(request: web.Request) -> web.Response:
    """Эндпоинт для проверки здоровья (Hugging Face Spaces & Uptime monitor)."""
    html_content = (
        "<!DOCTYPE html>"
        "<html><head><title>Markify Bot</title>"
        "<meta charset='utf-8'>"
        "<style>body { font-family: system-ui, sans-serif; background: #0f1117; color: #fff; display: flex; "
        "align-items: center; justify-content: center; height: 100vh; margin: 0; }"
        ".card { background: #1a1d24; border: 1px solid #2a2e39; border-radius: 12px; padding: 32px; "
        "text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.4); max-width: 400px; }"
        "h1 { color: #00d2ff; margin-bottom: 8px; font-size: 24px; }"
        ".badge { display: inline-block; background: #10b981; color: #fff; padding: 4px 12px; "
        "border-radius: 20px; font-weight: 600; font-size: 13px; margin: 12px 0; }"
        "p { color: #9ca3af; font-size: 14px; line-height: 1.5; margin: 0; }"
        "</style></head><body>"
        "<div class='card'>"
        "<h1>Markify Bot 🎨</h1>"
        "<div class='badge'>● RUNNING 24/7</div>"
        "<p>Telegram bot engine is active and ready to process photos.</p>"
        "</div></body></html>"
    )
    return web.Response(text=html_content, content_type="text/html")


async def start_web_server(port: int) -> web.AppRunner:
    """Запускает легкий aiohttp веб-сервер для Hugging Face Spaces."""
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner


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

    # Регистрация middleware для альбомов
    image_router.message.middleware(AlbumMiddleware())

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(settings_router)
    dp.include_router(image_router)

    await set_bot_commands(bot)
    logger.info("Markify Bot успешно запущен и ожидает сообщений...")

    port = int(os.getenv("PORT", "7860"))
    web_runner = None
    try:
        web_runner = await start_web_server(port)
        logger.info(f"Веб-сервер статуса успешно запущен на 0.0.0.0:{port}")
    except Exception as e:
        logger.warning(f"Не удалось запустить веб-сервер на порту {port}: {e}")

    try:
        # Сброс накопившихся апдейтов и старт поллинга
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
