"""Минималистичные и удобные инлайн-клавиатуры."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.database.models import UserSettings

POSITION_NAMES = {
    "bottom_right": "↘️ Правый нижний",
    "bottom_left": "↙️ Левый нижний",
    "top_right": "↗️ Правый верхний",
    "top_left": "↖️ Левый верхний",
}

SCALE_NAMES = {
    "small": "14% (Малый)",
    "medium": "18% (Стандарт)",
    "large": "25% (Большой)",
}


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Компактное главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="🎨 Свой логотип", callback_data="logo:upload"),
            ],
            [
                InlineKeyboardButton(text="👁 Превью", callback_data="logo:preview"),
                InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu:help"),
            ],
        ]
    )


def get_settings_kb(settings: UserSettings) -> InlineKeyboardMarkup:
    """Лаконичное меню настроек."""
    color_status = "Вкл" if settings.auto_color else "Выкл"
    pos_label = POSITION_NAMES.get(settings.logo_position, "↘️ Правый нижний")
    scale_label = SCALE_NAMES.get(settings.logo_scale, "18%")
    opacity_label = f"{settings.logo_opacity}%"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Угол: {pos_label}",
                callback_data="cycle:position",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Размер: {scale_label}",
                callback_data="cycle:scale",
            ),
            InlineKeyboardButton(
                text=f"Прозрачность: {opacity_label}",
                callback_data="cycle:opacity",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Автокоррекция: {color_status}",
                callback_data="toggle:autocolor",
            )
        ],
        [
            InlineKeyboardButton(text="🎨 Загрузить лого", callback_data="logo:upload"),
            InlineKeyboardButton(text="👁 Превью", callback_data="logo:preview"),
        ],
    ]

    if settings.has_custom_logo:
        keyboard.append([
            InlineKeyboardButton(
                text="🗑 Сбросить логотип",
                callback_data="logo:delete",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_upload_kb() -> InlineKeyboardMarkup:
    """Отмена загрузки логотипа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="logo:cancel_upload")]
        ]
    )


def get_back_to_settings_kb() -> InlineKeyboardMarkup:
    """Возврат в настройки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="menu:settings")]
        ]
    )
