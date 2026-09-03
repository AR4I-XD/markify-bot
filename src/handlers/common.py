"""Базовые команды бота: /start, /help, главное меню."""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.keyboards.inline import get_main_menu_kb

router = Router(name="common")


def format_welcome_text(first_name: str, has_custom_logo: bool) -> str:
    logo_status = "🎨 Ваш персональный логотип" if has_custom_logo else "✨ Стандартный логотип Markify"
    return (
        f"👋 Привет, <b>{first_name}</b>!\n\n"
        f"Я бот <b>Markify</b>. Я наношу логотип на ваши фотографии и делаю автоцветокоррекцию.\n\n"
        f"<b>Особенности:</b>\n"
        f"• 📐 Логотип всегда <b>пропорционален и аккуратно в правом нижнем углу</b>.\n"
        f"• 🪄 <b>Автоцветокор</b> делает фото живее и сочнее.\n"
        f"• 🛡️ <b>Конфиденциальность</b>: ваши фото не сохраняются на сервере (Zero-Storage).\n\n"
        f"Текущий логотип: <b>{logo_status}</b>\n\n"
        f"👉 <b>Просто пришлите мне фото</b> (как обычное сжатое изображение или как файл без сжатия)!"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(message.from_user.id)
    text = format_welcome_text(message.from_user.first_name, user_settings.has_custom_logo)
    await message.answer(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    help_text = (
        "<b>📖 Как пользоваться ботом Markify:</b>\n\n"
        "1. <b>Обработка фото:</b> отправьте боту любую фотографию. Бот обработает её и сразу пришлет результат.\n"
        "2. <b>Максимальное качество:</b> отправляйте фото как «Файл / Документ» без сжатия — бот вернет несжатый оригинал с логотипом.\n"
        "3. <b>Свой логотип:</b> перейдите в ⚙️ Настройки и нажмите «Загрузить свой лого». Отправьте PNG-файл с прозрачным фоном.\n"
        "4. <b>Настройки:</b> можно включать/отключать автоцветокоррекцию, менять размер и прозрачность логотипа.\n"
        "5. <b>Безопасность:</b> бот обрабатывает фото исключительно в оперативной памяти и не хранит ваши снимки."
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_settings = await db.get_user_settings(callback.from_user.id)
    text = format_welcome_text(callback.from_user.first_name, user_settings.has_custom_logo)
    await callback.message.edit_text(text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help_menu(callback: CallbackQuery):
    help_text = (
        "<b>📖 Как пользоваться ботом Markify:</b>\n\n"
        "1. <b>Обработка фото:</b> отправьте фото обычным сообщением или файлом.\n"
        "2. <b>Свой логотип:</b> загрузите PNG с прозрачным фоном через меню «Настройки».\n"
        "3. <b>Автоцветокоррекция:</b> улучшает цвета и контраст каждого кадра.\n"
        "4. <b>Zero-Storage:</b> мы не сохраняем ваши фото на сервере."
    )
    await callback.message.edit_text(help_text, reply_markup=get_main_menu_kb(), parse_mode="HTML")
    await callback.answer()
