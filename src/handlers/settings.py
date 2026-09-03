"""Обработчики меню настроек и загрузки логотипа."""

import io
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from PIL import Image

from src.database.db import db
from src.database.models import UserSettings
from src.keyboards.inline import (
    get_back_to_settings_kb,
    get_cancel_upload_kb,
    get_settings_kb,
)
from src.services.watermark import process_image

router = Router(name="settings")


class UploadLogoStates(StatesGroup):
    waiting_for_logo = State()


def format_settings_text(settings: UserSettings) -> str:
    logo_type = "🎨 Ваш кастомный логотип" if settings.has_custom_logo else "✨ Стандартный водяной знак"
    color_type = "Включена (улучшает сочность и контраст)" if settings.auto_color else "Выключена"
    
    scale_names = {
        "small": "Маленький (14%)",
        "medium": "Средний (18%)",
        "large": "Большой (25%)",
    }
    scale_type = scale_names.get(settings.logo_scale, "Средний")

    return (
        "<b>⚙️ Настройки брендирования:</b>\n\n"
        f"• <b>Логотип:</b> {logo_type}\n"
        f"• <b>Автоцветокоррекция:</b> {color_type}\n"
        f"• <b>Размер водяного знака:</b> {scale_type}\n"
        f"• <b>Прозрачность:</b> {settings.logo_opacity}%\n\n"
        "Нажимайте на кнопки ниже, чтобы переключить параметры или загрузить свой логотип:"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(message.from_user.id)
    text = format_settings_text(settings)
    await message.answer(text, reply_markup=get_settings_kb(settings), parse_mode="HTML")


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(callback.from_user.id)
    text = format_settings_text(settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(settings), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "toggle:autocolor")
async def cb_toggle_autocolor(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    new_status = not settings.auto_color
    updated_settings = await db.update_settings(callback.from_user.id, auto_color=new_status)
    
    text = format_settings_text(updated_settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(updated_settings), parse_mode="HTML")
    await callback.answer(f"Автоцветокоррекция: {'Включена' if new_status else 'Выключена'}")


@router.callback_query(F.data == "cycle:scale")
async def cb_cycle_scale(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    scale_order = ["small", "medium", "large"]
    curr_idx = scale_order.index(settings.logo_scale) if settings.logo_scale in scale_order else 1
    next_scale = scale_order[(curr_idx + 1) % len(scale_order)]

    updated_settings = await db.update_settings(callback.from_user.id, logo_scale=next_scale)
    text = format_settings_text(updated_settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(updated_settings), parse_mode="HTML")
    await callback.answer(f"Размер: {next_scale}")


@router.callback_query(F.data == "cycle:opacity")
async def cb_cycle_opacity(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    opacity_order = [100, 80, 60]
    curr_idx = opacity_order.index(settings.logo_opacity) if settings.logo_opacity in opacity_order else 0
    next_opacity = opacity_order[(curr_idx + 1) % len(opacity_order)]

    updated_settings = await db.update_settings(callback.from_user.id, logo_opacity=next_opacity)
    text = format_settings_text(updated_settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(updated_settings), parse_mode="HTML")
    await callback.answer(f"Прозрачность: {next_opacity}%")


@router.callback_query(F.data == "logo:delete")
async def cb_delete_logo(callback: CallbackQuery):
    await db.delete_user_logo(callback.from_user.id)
    settings = await db.get_user_settings(callback.from_user.id)
    text = format_settings_text(settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(settings), parse_mode="HTML")
    await callback.answer("Кастомный логотип удален. Используется стандартный водяной знак.")


@router.callback_query(F.data == "logo:upload")
async def cb_start_upload_logo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UploadLogoStates.waiting_for_logo)
    text = (
        "<b>🎨 Загрузка вашего логотипа:</b>\n\n"
        "Отправьте логотип <b>файлом (документом) в формате PNG</b> с прозрачным фоном.\n\n"
        "💡 <i>Совет: отправка файлом без сжатия гарантирует сохранение прозрачности и максимальную четкость!</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_upload_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "logo:cancel_upload")
async def cb_cancel_upload_logo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(callback.from_user.id)
    text = format_settings_text(settings)
    await callback.message.edit_text(text, reply_markup=get_settings_kb(settings), parse_mode="HTML")
    await callback.answer("Загрузка логотипа отменена.")


@router.message(UploadLogoStates.waiting_for_logo, F.document)
@router.message(UploadLogoStates.waiting_for_logo, F.photo)
async def handle_logo_upload(message: Message, state: FSMContext, bot: Bot):
    # Получаем файл от пользователя в буфер памяти
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id

    if not file_id:
        await message.answer("Пожалуйста, отправьте изображение или документ с логотипом.")
        return

    buffer = io.BytesIO()
    await bot.download(file_id, destination=buffer)
    buffer.seek(0)

    try:
        logo_img = Image.open(buffer)
        logo_img.load()
        # Преобразуем в RGBA для гарантии прозрачности
        if logo_img.mode != "RGBA":
            logo_img = logo_img.convert("RGBA")

        # Сохраняем в оптимизированном PNG виде
        save_buf = io.BytesIO()
        logo_img.save(save_buf, format="PNG")
        logo_bytes = save_buf.getvalue()

        await db.save_user_logo(message.from_user.id, logo_bytes)
        await state.clear()

        # Создаем превью-демонстрацию
        sample_img = Image.new("RGB", (1200, 800), (35, 42, 54))
        sample_buf = io.BytesIO()
        sample_img.save(sample_buf, format="JPEG")

        preview_buf = process_image(
            image_input=sample_buf.getvalue(),
            logo_input=logo_bytes,
            auto_color=False,
            scale="medium",
            opacity=100,
        )

        preview_file = BufferedInputFile(preview_buf.getvalue(), filename="logo_preview.jpg")
        settings = await db.get_user_settings(message.from_user.id)

        await message.answer_photo(
            photo=preview_file,
            caption="🎉 <b>Логотип успешно сохранен!</b>\n\nВыше показано тестовое превью его размещения в правом нижнем углу.",
            parse_mode="HTML",
            reply_markup=get_back_to_settings_kb(),
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при обработке файла: {e}\nУбедитесь, что это корректное изображение в формате PNG или JPG.",
            reply_markup=get_cancel_upload_kb(),
        )


@router.callback_query(F.data == "logo:preview")
async def cb_preview_logo(callback: CallbackQuery):
    try:
        logo_bytes = await db.get_effective_logo_bytes(callback.from_user.id)
        settings = await db.get_user_settings(callback.from_user.id)

        # Создаем тестовую подложку 1200x800
        sample_img = Image.new("RGB", (1200, 800), (30, 36, 48))
        sample_buf = io.BytesIO()
        sample_img.save(sample_buf, format="JPEG")

        preview_buf = process_image(
            image_input=sample_buf.getvalue(),
            logo_input=logo_bytes,
            auto_color=False,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
        )

        preview_file = BufferedInputFile(preview_buf.getvalue(), filename="preview.jpg")
        logo_desc = "Ваш кастомный логотип" if settings.has_custom_logo else "Стандартный водяной знак Markify"

        await callback.message.answer_photo(
            photo=preview_file,
            caption=f"👁 <b>Превью водяного знака:</b>\n\n• Тип: {logo_desc}\n• Размер: {settings.logo_scale}\n• Прозрачность: {settings.logo_opacity}%",
            parse_mode="HTML",
            reply_markup=get_back_to_settings_kb(),
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка при создании превью: {e}", show_alert=True)
