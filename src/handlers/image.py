"""Обработчик входящих фотографий, альбомов и документов (Zero-Storage)."""

import asyncio
import io
from typing import List, Optional
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, BufferedInputFile, InputMediaDocument

from src.database.db import db
from src.services.watermark import process_image

router = Router(name="image_processing")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_MEDIA_GROUP_SIZE = 10  # Ограничение Telegram Bot API на размер медиагруппы


async def process_single_image(
    bot: Bot,
    file_id: str,
    logo_bytes: bytes,
    auto_color: bool,
    scale: str,
    opacity: int,
    position: str,
    original_filename: Optional[str] = None,
) -> tuple[str, bytes]:
    """Загружает и обрабатывает одно изображение в памяти, возвращая имя файла и байты."""
    in_buffer = io.BytesIO()
    await bot.download(file_id, destination=in_buffer)
    image_bytes = in_buffer.getvalue()
    in_buffer.close()

    # Определение формата вывода
    filename = (original_filename or "").lower()
    if filename.endswith(".png"):
        out_fmt = "PNG"
        ext = ".png"
    else:
        out_fmt = "JPEG"
        ext = ".jpg"

    result_buffer = await asyncio.to_thread(
        process_image,
        image_input=image_bytes,
        logo_input=logo_bytes,
        auto_color=auto_color,
        scale=scale,
        opacity=opacity,
        position=position,
        output_format=out_fmt,
    )
    result_bytes = result_buffer.getvalue()
    result_buffer.close()

    final_name = f"markify_{filename}" if filename else f"markified{ext}"
    return final_name, result_bytes


async def send_processed_documents(
    message: Message,
    processed_items: List[tuple[str, bytes]],
):
    """Отправляет обработанные изображения строго файлами (документами) без сжатия.

    Если элементов больше 10, разбивает их на допустимые группы Telegram (2..10).
    """
    if not processed_items:
        return

    if len(processed_items) == 1:
        filename, file_bytes = processed_items[0]
        output_file = BufferedInputFile(file_bytes, filename=filename)
        await message.reply_document(document=output_file)
        return

    # Разбивка на чанки до 10 файлов
    for i in range(0, len(processed_items), MAX_MEDIA_GROUP_SIZE):
        chunk = processed_items[i : i + MAX_MEDIA_GROUP_SIZE]
        if len(chunk) == 1:
            filename, file_bytes = chunk[0]
            output_file = BufferedInputFile(file_bytes, filename=filename)
            await message.answer_document(document=output_file)
        else:
            media_group = [
                InputMediaDocument(media=BufferedInputFile(f_bytes, filename=fname))
                for fname, f_bytes in chunk
            ]
            await message.answer_media_group(media=media_group)
        # Небольшая пауза между группами для соблюдения лимитов Telegram
        if i + MAX_MEDIA_GROUP_SIZE < len(processed_items):
            await asyncio.sleep(0.5)


@router.message(F.photo)
async def handle_incoming_photo(
    message: Message,
    bot: Bot,
    album: Optional[List[Message]] = None,
):
    """Обработка фотографий (одиночных или альбомов) с гарантированной отправкой файлами."""
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    logo_bytes = await db.get_effective_logo_bytes(user_id)

    # 1. Альбом фотографий
    if album and len(album) > 1:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        try:
            tasks = [
                process_single_image(
                    bot=bot,
                    file_id=msg.photo[-1].file_id,
                    logo_bytes=logo_bytes,
                    auto_color=settings.auto_color,
                    scale=settings.logo_scale,
                    opacity=settings.logo_opacity,
                    position=settings.logo_position,
                    original_filename=f"photo_{idx + 1}.jpg",
                )
                for idx, msg in enumerate(album)
                if msg.photo
            ]
            processed_items = await asyncio.gather(*tasks)
            await send_processed_documents(message, processed_items)
        except Exception as e:
            await message.reply(f"Ошибка при обработке альбома: {e}")
        return

    # 2. Одиночное фото
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    try:
        filename, photo_bytes = await process_single_image(
            bot=bot,
            file_id=message.photo[-1].file_id,
            logo_bytes=logo_bytes,
            auto_color=settings.auto_color,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            position=settings.logo_position,
            original_filename="photo.jpg",
        )
        await send_processed_documents(message, [(filename, photo_bytes)])
    except Exception as e:
        await message.reply(f"Ошибка при обработке: {e}")


@router.message(F.document)
async def handle_incoming_document(
    message: Message,
    bot: Bot,
    album: Optional[List[Message]] = None,
):
    """Обработка несжатых изображений (документов), включая альбомы документов."""
    document = message.document
    filename = (document.file_name or "").lower()
    mime_type = (document.mime_type or "").lower()

    is_image = mime_type.startswith("image/") or any(filename.endswith(ext) for ext in IMAGE_EXTENSIONS)
    if not is_image:
        return

    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    logo_bytes = await db.get_effective_logo_bytes(user_id)

    # Альбом документов
    if album and len(album) > 1:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        try:
            tasks = [
                process_single_image(
                    bot=bot,
                    file_id=msg.document.file_id,
                    logo_bytes=logo_bytes,
                    auto_color=settings.auto_color,
                    scale=settings.logo_scale,
                    opacity=settings.logo_opacity,
                    position=settings.logo_position,
                    original_filename=msg.document.file_name or f"doc_{idx + 1}.jpg",
                )
                for idx, msg in enumerate(album)
                if msg.document
            ]
            processed_items = await asyncio.gather(*tasks)
            await send_processed_documents(message, processed_items)
        except Exception as e:
            await message.reply(f"Ошибка при обработке файлов: {e}")
        return

    # Одиночный документ
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    try:
        filename, doc_bytes = await process_single_image(
            bot=bot,
            file_id=document.file_id,
            logo_bytes=logo_bytes,
            auto_color=settings.auto_color,
            scale=settings.logo_scale,
            opacity=settings.logo_opacity,
            position=settings.logo_position,
            original_filename=document.file_name,
        )
        await send_processed_documents(message, [(filename, doc_bytes)])
    except Exception as e:
        await message.reply(f"Ошибка при обработке файла: {e}")
