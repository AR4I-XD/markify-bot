"""Минималистичные и удобные инлайн-клавиатуры."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.database.models import UserSettings

POSITION_NAMES = {
    "bottom_right": "↘️ Снизу справа",
    "bottom_left": "↙️ Снизу слева",
    "top_left": "↖️ Сверху слева",
    "top_right": "↗️ Сверху справа",
}

SCALE_NAMES = {
    "small": "14% (Малый)",
    "medium": "18% (Стандарт)",
    "large": "25% (Большой)",
}


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Сбалансированное главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="👁 Превью", callback_data="logo:preview"),
            ],
            [
                InlineKeyboardButton(text="🎨 Загрузить лого", callback_data="logo:upload"),
                InlineKeyboardButton(text="ℹ️ Справка", callback_data="menu:help"),
            ],
        ]
    )


def get_settings_kb(settings: UserSettings) -> InlineKeyboardMarkup:
    """Лаконичное и отзывчивое меню настроек с оптимальной длиной кнопок."""
    color_badge = "Вкл ✅" if settings.auto_color else "Выкл ❌"
    mode_badge = "⚡ Сразу" if settings.process_mode == "auto" else "⏳ По кнопке"
    pos_label = POSITION_NAMES.get(settings.logo_position, "↘️ Снизу справа")
    scale_val = {"small": "14%", "medium": "18%", "large": "25%"}.get(settings.logo_scale, "18%")
    opacity_val = f"{settings.logo_opacity}%"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Режим: {mode_badge}",
                callback_data="toggle:processmode",
            ),
            InlineKeyboardButton(
                text=f"Автоцвет: {color_badge}",
                callback_data="toggle:autocolor",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Положение: {pos_label}",
                callback_data="cycle:position",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Размер: {scale_val}",
                callback_data="cycle:scale",
            ),
            InlineKeyboardButton(
                text=f"Прозрачность: {opacity_val}",
                callback_data="cycle:opacity",
            ),
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
        InlineKeyboardButton(text="◀️ В главное меню", callback_data="menu:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_preview_nav_kb() -> InlineKeyboardMarkup:
    """Навигация под фото превью."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:main"),
            ]
        ]
    )


def get_help_kb() -> InlineKeyboardMarkup:
    """Навигация для экрана помощи/справки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:main"),
            ]
        ]
    )


def get_batch_confirm_kb(count: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения обработки очереди фото."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🚀 Обработать ({count} фото)",
                    callback_data="batch:start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Очистить очередь",
                    callback_data="batch:clear",
                )
            ],
        ]
    )


def get_cancel_upload_kb() -> InlineKeyboardMarkup:
    """Отмена загрузки логотипа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="logo:cancel_upload")]
        ]
    )


def get_back_to_settings_kb() -> InlineKeyboardMarkup:
    """Возврат в настройки (для обратной совместимости)."""
    return get_preview_nav_kb()

