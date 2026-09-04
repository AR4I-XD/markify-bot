"""Реплай-клавиатуры, закрепленные в нижней панели ввода Telegram."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def get_batch_reply_kb(count: int) -> ReplyKeyboardMarkup:
    """Нижняя панель действий для режима подтверждения.

    Всегда зафиксирована внизу экрана (в поле ввода), не прокручивается
    и не теряется среди десятков отправленных фотографий.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"🚀 Обработать ({count} фото)")],
            [KeyboardButton(text="🗑 Очистить очередь")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="Нажмите «🚀 Обработать» для запуска...",
    )


def get_remove_kb() -> ReplyKeyboardRemove:
    """Удаляет нижнюю панель кнопок."""
    return ReplyKeyboardRemove()
