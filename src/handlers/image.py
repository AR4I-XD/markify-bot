"""Обработчик входящих фотографий, альбомов и документов с пакетной очередью (Zero-Storage)."""

import asyncio
import io
from pathlib import Path
from typing import List, Optional
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaDocument, FSInputFile

from src.database.db import db
from src.keyboards.reply import get_batch_reply_kb, get_remove_kb
from src.services.batch_queue import batch_queue
from src.services.watermark import process_image

router = Router(name="image_processing")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_MEDIA_GROUP_SIZE = 10  # Ограничение Telegram Bot API на размер медиагруппы
CONCURRENCY_LIMIT = 2     # Ограничение параллельных задач для защиты оперативной памяти (100+ фото)

SUBWAY_GIF_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "subway.gif"
_cached_subway_file_id: Optional[str] = None


async def send_processing_status_animation(
    bot: Bot,
    chat_id: int,
    caption: str,
    reply_markup=None,
) -> Message:
    """Отправляет gif subway.gif со статусом обработки (с кэшированием file_id)."""
    global _cached_subway_file_id

    if _cached_subway_file_id:
        try:
            return await bot.send_animation(
                chat_id=chat_id,
                animation=_cached_subway_file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        except Exception:
            _cached_subway_file_id = None

    if SUBWAY_GIF_PATH.exists():
        try:
            msg = await bot.send_animation(
                chat_id=chat_id,
                animation=FSInputFile(str(SUBWAY_GIF_PATH)),
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            if msg.animation and msg.animation.file_id:
                _cached_subway_file_id = msg.animation.file_id
            return msg
        except Exception:
            pass

    return await bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def process_single_image_with_semaphore(
    sem: asyncio.Semaphore,
    bot: Bot,
    file_id: str,
    logo_bytes: bytes,
    auto_color: bool,
    scale: str,
    opacity: int,
    position: str,
    original_filename: Optional[str] = None,
) -> tuple[str, bytes]:
    """Обрабатывает одно изображение с ограничением одновременных задач в памяти."""
    async with sem:
        in_buffer = io.BytesIO()
        await bot.download(file_id, destination=in_buffer)
        image_bytes = in_buffer.getvalue()
        in_buffer.close()

        filename = (original_filename or "").lower()
        out_fmt = "PNG" if filename.endswith(".png") else "JPEG"
        ext = ".png" if out_fmt == "PNG" else ".jpg"

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
    bot: Bot,
    chat_id: int,
    processed_items: List[tuple[str, bytes]],
):
    """Отправляет готовые файлы пачками по 10 штук без сжатия."""
    if not processed_items:
        return

    if len(processed_items) == 1:
        filename, file_bytes = processed_items[0]
        output_file = BufferedInputFile(file_bytes, filename=filename)
        await bot.send_document(chat_id=chat_id, document=output_file)
        return

    for i in range(0, len(processed_items), MAX_MEDIA_GROUP_SIZE):
        chunk = processed_items[i : i + MAX_MEDIA_GROUP_SIZE]
        if len(chunk) == 1:
            filename, file_bytes = chunk[0]
            output_file = BufferedInputFile(file_bytes, filename=filename)
            await bot.send_document(chat_id=chat_id, document=output_file)
        else:
            media_group = [
                InputMediaDocument(media=BufferedInputFile(f_bytes, filename=fname))
                for fname, f_bytes in chunk
            ]
            await bot.send_media_group(chat_id=chat_id, media=media_group)
        # Пауза для защиты от лимитов отправки Telegram
        if i + MAX_MEDIA_GROUP_SIZE < len(processed_items):
            await asyncio.sleep(0.6)


def format_progress_text(current: int, total: int) -> str:
    """Генерирует аккуратный прогресс-бар для пакетной обработки."""
    if total <= 1:
        return "⚡ <b>Обработка фото...</b>"

    percent = int((current / total) * 100) if total > 0 else 0
    bar_length = 8
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "▰" * filled + "▱" * (bar_length - filled)
    return (
        f"⚡ <b>Обработка: {current} из {total} фото ({percent}%)</b>\n"
        f"<code>[{bar}]</code>"
    )


async def update_bottom_queue_menu(message: Message, user_id: int, count: int):
    """Обновляет нижнюю панель кнопок и держит единственное лаконичное сообщение внизу."""
    reply_kb = get_batch_reply_kb(count)
    prev_msg_id = batch_queue.get_status_message_id(user_id)

    # Отправляем одно единственное сообщение с закреплением нижней панели
    new_msg = await message.answer(
        f"📥 В очереди: <b>{count} фото</b>",
        reply_markup=reply_kb,
        parse_mode="HTML",
    )
    batch_queue.set_status_message(user_id, new_msg.message_id)

    # Удаляем предыдущее сообщение со старым количеством, чтобы чат не засорялся
    if prev_msg_id and prev_msg_id != new_msg.message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
        except Exception:
            pass


@router.message(F.photo)
async def handle_incoming_photo(
    message: Message,
    bot: Bot,
    album: Optional[List[Message]] = None,
):
    """Прием фотографий (одиночных или альбомов)."""
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)

    incoming_items: List[tuple[str, str]] = []
    if album and len(album) > 1:
        for idx, msg in enumerate(album):
            if msg.photo:
                incoming_items.append((msg.photo[-1].file_id, f"photo_{idx + 1}.jpg"))
    elif message.photo:
        incoming_items.append((message.photo[-1].file_id, "photo.jpg"))

    if not incoming_items:
        return

    # 1. Режим «По подтверждению»: обновляем меню снизу
    if settings.process_mode == "confirm":
        total_count = batch_queue.add_items(user_id, incoming_items, message.chat.id)
        await update_bottom_queue_menu(message, user_id, total_count)
        return

    # 2. Режим «Сразу»: статусное сообщение с прогрессом и автоудалением
    total_items = len(incoming_items)
    init_status = format_progress_text(0, total_items) if total_items > 1 else "⚡ <b>Обработка фото...</b>"
    status_msg = await send_processing_status_animation(
        bot=bot,
        chat_id=message.chat.id,
        caption=init_status,
    )
    try:
        await process_and_dispatch_items(
            bot=bot,
            chat_id=message.chat.id,
            user_id=user_id,
            items=incoming_items,
            status_message=status_msg,
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass


@router.message(F.document)
async def handle_incoming_document(
    message: Message,
    bot: Bot,
    album: Optional[List[Message]] = None,
):
    """Прием несжатых документов-изображений."""
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)

    incoming_items: List[tuple[str, str]] = []
    if album and len(album) > 1:
        for idx, msg in enumerate(album):
            if msg.document:
                fname = msg.document.file_name or f"doc_{idx + 1}.jpg"
                incoming_items.append((msg.document.file_id, fname))
    elif message.document:
        fname = (message.document.file_name or "").lower()
        mime = (message.document.mime_type or "").lower()
        if mime.startswith("image/") or any(fname.endswith(ext) for ext in IMAGE_EXTENSIONS):
            incoming_items.append((message.document.file_id, message.document.file_name or "photo.jpg"))

    if not incoming_items:
        return

    if settings.process_mode == "confirm":
        total_count = batch_queue.add_items(user_id, incoming_items, message.chat.id)
        await update_bottom_queue_menu(message, user_id, total_count)
        return

    # Режим «Сразу»
    total_items = len(incoming_items)
    init_status = format_progress_text(0, total_items) if total_items > 1 else "⚡ <b>Обработка документа...</b>"
    status_msg = await send_processing_status_animation(
        bot=bot,
        chat_id=message.chat.id,
        caption=init_status,
    )
    try:
        await process_and_dispatch_items(
            bot=bot,
            chat_id=message.chat.id,
            user_id=user_id,
            items=incoming_items,
            status_message=status_msg,
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass


async def process_and_dispatch_items(
    bot: Bot,
    chat_id: int,
    user_id: int,
    items: List[tuple[str, str]],
    status_message: Optional[Message] = None,
):
    """Главный конвейер обработки пачки фото с контролем памяти и отправкой без сжатия."""
    settings = await db.get_user_settings(user_id)
    logo_bytes = await db.get_effective_logo_bytes(user_id)
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

    total = len(items)
    processed_items: List[tuple[str, bytes]] = []

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

    for idx, (file_id, fname) in enumerate(items, 1):
        if status_message and total > 1 and (idx % 3 == 0 or idx == total or total <= 6):
            try:
                if status_message.animation or status_message.caption is not None:
                    await status_message.edit_caption(
                        caption=format_progress_text(idx, total),
                        parse_mode="HTML",
                    )
                else:
                    await status_message.edit_text(
                        format_progress_text(idx, total),
                        parse_mode="HTML",
                    )
            except Exception:
                pass

        try:
            item_res = await process_single_image_with_semaphore(
                sem=sem,
                bot=bot,
                file_id=file_id,
                logo_bytes=logo_bytes,
                auto_color=settings.auto_color,
                scale=settings.logo_scale,
                opacity=settings.logo_opacity,
                position=settings.logo_position,
                original_filename=fname,
            )
            processed_items.append(item_res)
        except Exception:
            pass

    # Отправка результатов
    await send_processed_documents(bot, chat_id, processed_items)

    if status_message:
        try:
            await status_message.delete()
        except Exception:
            pass


# ==================== ОБРАБОТЧИКИ ЗАПУСКА ОЧЕРЕДИ ====================

@router.message(F.text.startswith("🚀 Обработать"))
async def handle_reply_batch_start(message: Message, bot: Bot):
    """Запуск обработки по нажатию нижней кнопки."""
    user_id = message.from_user.id
    items = batch_queue.pop_all(user_id)

    # Удаляем сообщение пользователя с текстом кнопки для чистоты чата
    try:
        await message.delete()
    except Exception:
        pass

    # Удаляем статусное сообщение очереди "В очереди: N фото"
    prev_msg_id = batch_queue.get_status_message_id(user_id)
    if prev_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
        except Exception:
            pass

    if not items:
        await message.answer("Очередь пуста.", reply_markup=get_remove_kb())
        return

    status_msg = await send_processing_status_animation(
        bot=bot,
        chat_id=message.chat.id,
        caption=format_progress_text(0, len(items)),
        reply_markup=get_remove_kb(),
    )
    await process_and_dispatch_items(
        bot=bot,
        chat_id=message.chat.id,
        user_id=user_id,
        items=items,
        status_message=status_msg,
    )


@router.message(F.text == "🗑 Очистить очередь")
async def handle_reply_batch_clear(message: Message, bot: Bot):
    """Очистка очереди по нажатию нижней кнопки."""
    user_id = message.from_user.id
    batch_queue.clear(user_id)
    try:
        await message.delete()
    except Exception:
        pass

    prev_msg_id = batch_queue.get_status_message_id(user_id)
    if prev_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
        except Exception:
            pass

    temp = await message.answer("🗑 <b>Очередь фото очищена.</b>", reply_markup=get_remove_kb(), parse_mode="HTML")
    await asyncio.sleep(2)
    try:
        await temp.delete()
    except Exception:
        pass


@router.callback_query(F.data == "batch:start")
async def cb_start_batch(callback: CallbackQuery, bot: Bot):
    """Запуск обработки инлайн-кнопкой (если осталась от старых сообщений)."""
    user_id = callback.from_user.id
    items = batch_queue.pop_all(user_id)

    if not items:
        await callback.answer("Очередь пуста.", show_alert=True)
        return

    await callback.answer("Начинаю обработку...")
    try:
        await callback.message.delete()
    except Exception:
        pass

    status_msg = await send_processing_status_animation(
        bot=bot,
        chat_id=callback.message.chat.id,
        caption=format_progress_text(0, len(items)),
    )
    await process_and_dispatch_items(
        bot=bot,
        chat_id=callback.message.chat.id,
        user_id=user_id,
        items=items,
        status_message=status_msg,
    )


@router.callback_query(F.data == "batch:clear")
async def cb_clear_batch(callback: CallbackQuery):
    """Очистка очереди инлайн-кнопкой."""
    user_id = callback.from_user.id
    batch_queue.clear(user_id)
    try:
        await callback.message.edit_text("🗑 <b>Очередь фото очищена.</b>", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Очередь очищена.")
