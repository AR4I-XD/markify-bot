"""Инлайн-клавиатуры для навигации и управления настройками."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.database.models import UserSettings


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Главная клавиатура быстрого доступа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="🎨 Загрузить логотип", callback_data="logo:upload"),
            ],
            [
                InlineKeyboardButton(text="👁 Посмотреть превью логотипа", callback_data="logo:preview"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Инструкция", callback_data="menu:help"),
            ],
        ]
    )


def get_settings_kb(settings: UserSettings) -> InlineKeyboardMarkup:
    """Клавиатура меню настроек с динамическими индикаторами."""
    # Индикатор автоцветокоррекции
    color_status = "✅ Вкл" if settings.auto_color else "❌ Выкл"

    # Индикатор размера
    scale_names = {
        "small": "Маленький (14%)",
        "medium": "Средний (18%)",
        "large": "Большой (25%)",
    }
    current_scale = scale_names.get(settings.logo_scale, "Средний")

    # Индикатор прозрачности
    current_opacity = f"{settings.logo_opacity}%"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"🪄 Автоцветокор: {color_status}",
                callback_data="toggle:autocolor",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"📐 Размер лого: {current_scale}",
                callback_data="cycle:scale",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💧 Прозрачность: {current_opacity}",
                callback_data="cycle:opacity",
            )
        ],
        [
            InlineKeyboardButton(text="🎨 Загрузить свой лого", callback_data="logo:upload"),
            InlineKeyboardButton(text="👁 Превью", callback_data="logo:preview"),
        ],
    ]

    # Если установлен кастомный логотип — показываем кнопку удаления
    if settings.has_custom_logo:
        keyboard.append([
            InlineKeyboardButton(
                text="🗑 Сбросить на стандартный логотип",
                callback_data="logo:delete",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_upload_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены при загрузке логотипа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="logo:cancel_upload")]
        ]
    )


def get_back_to_settings_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в настройки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Вернуться в настройки", callback_data="menu:settings")]
        ]
    )
