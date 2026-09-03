"""Обработчик входящих фотографий и документов (Zero-Storage)."""

import asyncio
import io
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, BufferedInputFile

from src.database.db import db
from src.services.watermark import process_image

router = Router(name="image_processing")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@router.message(F.photo)
async def handle_incoming_photo(message: Message, bot: Bot):
    """Обработка сжатой фотографии из Telegram."""
    user_id = message.from_user.id
    photo = message.photo[-1]  # Берем максимальное доступное разрешение

    # Показываем статус обработки в чате
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    # Загрузка фото строго в оперативную память (BytesIO)
    in_buffer = io.BytesIO()
    await bot.download(photo.file_id, destination=in_buffer)
    image_bytes = in_buffer.getvalue()

    try:
        # Получаем настройки и логотип
        settings = await db.get_user_settings(user_id)
        logo_bytes = await db.get_effective_logo_bytes(user_id)

        # Выполняем обработку в фоновом потоке, чтобы не блокировать event loop
        result_buffer = await asyncio.to_thread(
            process_image,
            image_input=image_bytes,
            logo_input=logo_bytes,
            auto_color=settings.auto_color,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            output_format="JPEG",
        )

        output_file = BufferedInputFile(
            file=result_buffer.getvalue(),
            filename="markified.jpg",
        )

        caption_parts = []
        if settings.auto_color:
            caption_parts.append("🪄 Автоцветокор")
        caption_parts.append("📐 Логотип в правом нижнем углу")
        caption = " ✅ Готово! (" + " | ".join(caption_parts) + ")"

        await message.reply_photo(photo=output_file, caption=caption)

    except Exception as e:
        await message.reply(f"❌ Ошибка при обработке изображения: {e}")
    finally:
        # Гарантированное освобождение буферов
        in_buffer.close()


@router.message(F.document)
async def handle_incoming_document(message: Message, bot: Bot):
    """Обработка несжатого изображения, отправленного файлом (без потери качества)."""
    document = message.document
    filename = (document.file_name or "").lower()
    mime_type = (document.mime_type or "").lower()

    is_image = mime_type.startswith("image/") or any(filename.endswith(ext) for ext in IMAGE_EXTENSIONS)
    if not is_image:
        # Если это не картинка, игнорируем или не перехватываем
        return

    user_id = message.from_user.id

    # Показываем статус загрузки документа
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)

    in_buffer = io.BytesIO()
    await bot.download(document.file_id, destination=in_buffer)
    image_bytes = in_buffer.getvalue()

    try:
        settings = await db.get_user_settings(user_id)
        logo_bytes = await db.get_effective_logo_bytes(user_id)

        # Определяем желаемый формат вывода по исходному файлу
        if filename.endswith(".png") or "png" in mime_type:
            out_fmt = "PNG"
            ext = ".png"
        else:
            out_fmt = "JPEG"
            ext = ".jpg"

        result_buffer = await asyncio.to_thread(
            process_image,
            image_input=image_bytes,
            logo_input=logo_bytes,
            auto_color=settings.auto_color,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            output_format=out_fmt,
        )

        out_filename = f"markify_{filename}" if filename else f"markify_photo{ext}"
        output_file = BufferedInputFile(
            file=result_buffer.getvalue(),
            filename=out_filename,
        )

        await message.reply_document(
            document=output_file,
            caption="✅ Готово! Файл обработан без потери исходного разрешения и качества.",
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка при обработке файла: {e}")
    finally:
        in_buffer.close()
