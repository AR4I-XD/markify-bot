"""Минималистичные базовые хэндлеры: /start, /help."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.keyboards.inline import get_main_menu_kb

router = Router(name="common")


def format_welcome_text(has_custom_logo: bool) -> str:
    logo_status = "Пользовательский" if has_custom_logo else "Стандартный"
    return (
        "<b>Markify</b> — брендирование и автокоррекция фото.\n\n"
        f"• Логотип: <b>{logo_status}</b>\n\n"
        "Отправьте фото или альбом для обработки."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(message.from_user.id)
    text = format_welcome_text(user_settings.has_custom_logo)
    await message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    help_text = (
        "<b>Инструкция Markify:</b>\n\n"
        "• <b>Обработка:</b> отправьте одно фото или сразу альбом. Бот вернет результат в том же виде.\n"
        "• <b>Без сжатия:</b> отправляйте как документ/файл для сохранения оригинального качества.\n"
        "• <b>Свой логотип:</b> в настройках выберите «Загрузить лого» (рекомендуется формат PNG с прозрачностью).\n"
        "• <b>Угол и размер:</b> настраиваются в меню настроек."
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(callback.from_user.id)
    text = format_welcome_text(user_settings.has_custom_logo)
    
    # Безопасное обновление: если исходное сообщение содержит медиа (фото/превью), удаляем и шлем текст
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help_menu(callback: CallbackQuery):
    help_text = (
        "<b>Инструкция Markify:</b>\n\n"
        "• <b>Обработка:</b> отправьте фото или альбом.\n"
        "• <b>Без сжатия:</b> отправляйте как файл/документ.\n"
        "• <b>Свой логотип:</b> загрузите PNG с прозрачным фоном через «Настройки».\n"
        "• <b>Угол и размер:</b> выбираются в «Настройках»."
    )
    try:
        await callback.message.edit_text(help_text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.delete()
        await callback.message.answer(help_text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    await callback.answer()
