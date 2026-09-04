"""Базовые хэндлеры пользовательского интерфейса: /start, /help, главное меню."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.database.models import UserSettings
from src.keyboards.inline import (
    POSITION_NAMES,
    get_main_menu_kb,
    get_help_kb,
)

router = Router(name="common")


def format_welcome_text(settings: UserSettings) -> str:
    """Генерирует лаконичный и информативный стартовый дашборд."""
    logo_status = "Пользовательский" if settings.has_custom_logo else "Стандартный"
    mode_status = "⚡ Сразу" if settings.process_mode == "auto" else "⏳ По кнопке"
    pos_status = POSITION_NAMES.get(settings.logo_position, "↘️ Снизу справа")
    color_status = "Вкл" if settings.auto_color else "Выкл"

    return (
        "<b>Markify</b> — брендирование и автокоррекция фото.\n\n"
        "⚙️ <b>Текущие параметры:</b>\n"
        f"• Режим: <b>{mode_status}</b>\n"
        f"• Логотип: <b>{logo_status}</b>\n"
        f"• Положение: <b>{pos_status}</b>\n"
        f"• Автокоррекция: <b>{color_status}</b>\n\n"
        "📷 <i>Отправьте фото или альбом для обработки.</i>"
    )


def format_help_text() -> str:
    """Единый структурированный текст справки."""
    return (
        "📖 <b>Справка и возможности Markify:</b>\n\n"
        "• <b>Обработка:</b> отправляйте одиночные фото или альбомы (до 100+ фото). Результат возвращается файлами в оригинальном качестве без сжатия.\n\n"
        "• <b>Режимы запуска:</b>\n"
        "  — <i>⚡ Сразу:</i> обработка стартует мгновенно при получении файлов.\n"
        "  — <i>⏳ По кнопке:</i> фото собираются в очередь, а обработка запускается по кнопке внизу экрана.\n\n"
        "• <b>Персональный логотип:</b> загрузите файл PNG с прозрачным фоном через «Настройки».\n\n"
        "• <b>Положение и масштаб:</b> выбирайте любой из 4 углов, масштаб и прозрачность водяного знака.\n\n"
        "• <b>Автокоррекция:</b> адаптивное улучшение баланса белого и контрастности."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(message.from_user.id)
    text = format_welcome_text(user_settings)
    await message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    text = format_help_text()
    await message.answer(text, reply_markup=get_help_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(callback.from_user.id)
    text = format_welcome_text(user_settings)
    
    # Безопасное обновление: если исходное сообщение содержит фото/превью, удаляем и отправляем текст
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help_menu(callback: CallbackQuery):
    text = format_help_text()
    try:
        await callback.message.edit_text(text, reply_markup=get_help_kb(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=get_help_kb(), parse_mode="HTML")
    await callback.answer()

