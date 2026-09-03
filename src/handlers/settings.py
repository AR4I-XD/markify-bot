"""Обработчики настроек брендирования и загрузки логотипа."""

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
    POSITION_NAMES,
    SCALE_NAMES,
    get_back_to_settings_kb,
    get_cancel_upload_kb,
    get_settings_kb,
)
from src.services.watermark import process_image

router = Router(name="settings")


class UploadLogoStates(StatesGroup):
    waiting_for_logo = State()


def format_settings_text(settings: UserSettings) -> str:
    logo_type = "Пользовательский" if settings.has_custom_logo else "Стандартный"
    color_type = "Вкл" if settings.auto_color else "Выкл"
    pos_type = POSITION_NAMES.get(settings.logo_position, "Правый нижний")
    scale_type = SCALE_NAMES.get(settings.logo_scale, "18%")

    return (
        "<b>Настройки брендирования:</b>\n\n"
        f"• Логотип: <b>{logo_type}</b>\n"
        f"• Положение: <b>{pos_type}</b>\n"
        f"• Размер: <b>{scale_type}</b>\n"
        f"• Прозрачность: <b>{settings.logo_opacity}%</b>\n"
        f"• Автокоррекция: <b>{color_type}</b>"
    )


async def send_or_edit_settings(message_or_call: Message | CallbackQuery, settings: UserSettings):
    """Надежный рендеринг экрана настроек (работает как с текстовыми, так и с медиа-сообщениями)."""
    text = format_settings_text(settings)
    kb = get_settings_kb(settings)

    if isinstance(message_or_call, Message):
        await message_or_call.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await message_or_call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            # Если исходное сообщение было фотографией (превью), удаляем его и отправляем свежее текстовое
            try:
                await message_or_call.message.delete()
            except Exception:
                pass
            await message_or_call.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(message.from_user.id)
    await send_or_edit_settings(message, settings)


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(callback.from_user.id)
    await send_or_edit_settings(callback, settings)
    await callback.answer()


@router.callback_query(F.data == "cycle:position")
async def cb_cycle_position(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    pos_order = ["bottom_right", "bottom_left", "top_left", "top_right"]
    curr_idx = pos_order.index(settings.logo_position) if settings.logo_position in pos_order else 0
    next_pos = pos_order[(curr_idx + 1) % len(pos_order)]

    updated_settings = await db.update_settings(callback.from_user.id, logo_position=next_pos)
    await send_or_edit_settings(callback, updated_settings)
    await callback.answer(f"Положение: {POSITION_NAMES.get(next_pos, next_pos)}")


@router.callback_query(F.data == "toggle:autocolor")
async def cb_toggle_autocolor(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    new_status = not settings.auto_color
    updated_settings = await db.update_settings(callback.from_user.id, auto_color=new_status)
    await send_or_edit_settings(callback, updated_settings)
    await callback.answer(f"Автокоррекция: {'Вкл' if new_status else 'Выкл'}")


@router.callback_query(F.data == "cycle:scale")
async def cb_cycle_scale(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    scale_order = ["small", "medium", "large"]
    curr_idx = scale_order.index(settings.logo_scale) if settings.logo_scale in scale_order else 1
    next_scale = scale_order[(curr_idx + 1) % len(scale_order)]

    updated_settings = await db.update_settings(callback.from_user.id, logo_scale=next_scale)
    await send_or_edit_settings(callback, updated_settings)
    await callback.answer(f"Размер: {SCALE_NAMES.get(next_scale, next_scale)}")


@router.callback_query(F.data == "cycle:opacity")
async def cb_cycle_opacity(callback: CallbackQuery):
    settings = await db.get_user_settings(callback.from_user.id)
    opacity_order = [100, 80, 60]
    curr_idx = opacity_order.index(settings.logo_opacity) if settings.logo_opacity in opacity_order else 0
    next_opacity = opacity_order[(curr_idx + 1) % len(opacity_order)]

    updated_settings = await db.update_settings(callback.from_user.id, logo_opacity=next_opacity)
    await send_or_edit_settings(callback, updated_settings)
    await callback.answer(f"Прозрачность: {next_opacity}%")


@router.callback_query(F.data == "logo:delete")
async def cb_delete_logo(callback: CallbackQuery):
    await db.delete_user_logo(callback.from_user.id)
    settings = await db.get_user_settings(callback.from_user.id)
    await send_or_edit_settings(callback, settings)
    await callback.answer("Логотип сброшен на стандартный")


@router.callback_query(F.data == "logo:upload")
async def cb_start_upload_logo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UploadLogoStates.waiting_for_logo)
    text = (
        "<b>Загрузка логотипа:</b>\n\n"
        "Отправьте изображение или файл (PNG с прозрачным фоном)."
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_upload_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_cancel_upload_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "logo:cancel_upload")
async def cb_cancel_upload_logo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    settings = await db.get_user_settings(callback.from_user.id)
    await send_or_edit_settings(callback, settings)
    await callback.answer("Отменено")


@router.message(UploadLogoStates.waiting_for_logo, F.document)
@router.message(UploadLogoStates.waiting_for_logo, F.photo)
async def handle_logo_upload(message: Message, state: FSMContext, bot: Bot):
    file_id = message.document.file_id if message.document else message.photo[-1].file_id

    buffer = io.BytesIO()
    await bot.download(file_id, destination=buffer)
    buffer.seek(0)

    try:
        logo_img = Image.open(buffer)
        logo_img.load()
        if logo_img.mode != "RGBA":
            logo_img = logo_img.convert("RGBA")

        save_buf = io.BytesIO()
        logo_img.save(save_buf, format="PNG")
        logo_bytes = save_buf.getvalue()

        await db.save_user_logo(message.from_user.id, logo_bytes)
        await state.clear()

        user_settings = await db.get_user_settings(message.from_user.id)

        # Превью нового логотипа
        sample_img = Image.new("RGB", (1200, 800), (32, 38, 48))
        sample_buf = io.BytesIO()
        sample_img.save(sample_buf, format="JPEG")

        preview_buf = process_image(
            image_input=sample_buf.getvalue(),
            logo_input=logo_bytes,
            auto_color=False,
            scale=user_settings.logo_scale,
            opacity=user_settings.logo_opacity,
            position=user_settings.logo_position,
        )

        preview_file = BufferedInputFile(preview_buf.getvalue(), filename="logo_preview.jpg")

        await message.answer_photo(
            photo=preview_file,
            caption="Логотип успешно сохранен.",
            reply_markup=get_back_to_settings_kb(),
        )
    except Exception as e:
        await message.answer(
            f"Не удалось распознать изображение: {e}",
            reply_markup=get_cancel_upload_kb(),
        )


@router.callback_query(F.data == "logo:preview")
async def cb_preview_logo(callback: CallbackQuery):
    try:
        logo_bytes = await db.get_effective_logo_bytes(callback.from_user.id)
        settings = await db.get_user_settings(callback.from_user.id)

        sample_img = Image.new("RGB", (1200, 800), (32, 38, 48))
        sample_buf = io.BytesIO()
        sample_img.save(sample_buf, format="JPEG")

        preview_buf = process_image(
            image_input=sample_buf.getvalue(),
            logo_input=logo_bytes,
            auto_color=False,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            position=settings.logo_position,
        )

        preview_file = BufferedInputFile(preview_buf.getvalue(), filename="preview.jpg")

        # Удаляем предыдущее меню перед показом превью, чтобы чат оставался аккуратным
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer_photo(
            photo=preview_file,
            caption="Превью размещения логотипа:",
            reply_markup=get_back_to_settings_kb(),
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка превью: {e}", show_alert=True)
