"""Обработчик входящих фотографий, альбомов и документов (Zero-Storage)."""

import asyncio
import io
from typing import List, Optional
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, BufferedInputFile, InputMediaPhoto

from src.database.db import db
from src.services.watermark import process_image

router = Router(name="image_processing")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


async def process_single_photo(
    bot: Bot,
    photo_file_id: str,
    logo_bytes: bytes,
    auto_color: bool,
    scale: str,
    opacity: int,
    position: str,
) -> bytes:
    """Загружает и обрабатывает одну фотографию строго в памяти."""
    in_buffer = io.BytesIO()
    await bot.download(photo_file_id, destination=in_buffer)
    image_bytes = in_buffer.getvalue()
    in_buffer.close()

    result_buffer = await asyncio.to_thread(
        process_image,
        image_input=image_bytes,
        logo_input=logo_bytes,
        auto_color=auto_color,
        scale=scale,
        opacity=opacity,
        position=position,
        output_format="JPEG",
    )
    result_bytes = result_buffer.getvalue()
    result_buffer.close()
    return result_bytes


@router.message(F.photo)
async def handle_incoming_photo(
    message: Message,
    bot: Bot,
    album: Optional[List[Message]] = None,
):
    """Обработка сжатых фотографий (как одиночных, так и отправленных группой/альбомом)."""
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    logo_bytes = await db.get_effective_logo_bytes(user_id)

    # 1. Если пришел альбом (несколько фото в одном сообщении)
    if album and len(album) > 1:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

        try:
            # Обрабатываем все фото из альбома
            tasks = [
                process_single_photo(
                    bot=bot,
                    photo_file_id=msg.photo[-1].file_id,
                    logo_bytes=logo_bytes,
                    auto_color=settings.auto_color,
                    scale=settings.logo_scale,
                    opacity=settings.logo_opacity,
                    position=settings.logo_position,
                )
                for msg in album
                if msg.photo
            ]
            processed_photos = await asyncio.gather(*tasks)

            # Собираем медиа-группу для отправки одним сообщением (без подписей)
            media_group = [
                InputMediaPhoto(media=BufferedInputFile(p_bytes, filename=f"photo_{idx}.jpg"))
                for idx, p_bytes in enumerate(processed_photos)
            ]

            await message.answer_media_group(media=media_group)

        except Exception as e:
            await message.reply(f"Ошибка при обработке альбома: {e}")
        return

    # 2. Одиночное фото
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    try:
        photo_bytes = await process_single_photo(
            bot=bot,
            photo_file_id=message.photo[-1].file_id,
            logo_bytes=logo_bytes,
            auto_color=settings.auto_color,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            position=settings.logo_position,
        )
        output_file = BufferedInputFile(photo_bytes, filename="markified.jpg")

        # Отправляем без подписи
        await message.reply_photo(photo=output_file)

    except Exception as e:
        await message.reply(f"Ошибка при обработке: {e}")


@router.message(F.document)
async def handle_incoming_document(message: Message, bot: Bot):
    """Обработка несжатого изображения (документа без потери качества)."""
    document = message.document
    filename = (document.file_name or "").lower()
    mime_type = (document.mime_type or "").lower()

    is_image = mime_type.startswith("image/") or any(filename.endswith(ext) for ext in IMAGE_EXTENSIONS)
    if not is_image:
        return

    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)

    in_buffer = io.BytesIO()
    await bot.download(document.file_id, destination=in_buffer)
    image_bytes = in_buffer.getvalue()
    in_buffer.close()

    try:
        settings = await db.get_user_settings(user_id)
        logo_bytes = await db.get_effective_logo_bytes(user_id)

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
            position=settings.logo_position,
            output_format=out_fmt,
        )

        out_filename = f"markify_{filename}" if filename else f"markify_photo{ext}"
        output_file = BufferedInputFile(
            file=result_buffer.getvalue(),
            filename=out_filename,
        )
        result_buffer.close()

        # Отправляем документ без подписи
        await message.reply_document(document=output_file)

    except Exception as e:
        await message.reply(f"Ошибка при обработке файла: {e}")
