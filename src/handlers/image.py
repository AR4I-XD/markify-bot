"""Обработчик входящих фотографий, альбомов и документов с пакетной очередью (Zero-Storage)."""

import asyncio
import io
from typing import List, Optional
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaDocument

from src.database.db import db
from src.keyboards.inline import get_batch_confirm_kb
from src.keyboards.reply import get_batch_reply_kb, get_remove_kb
from src.services.batch_queue import batch_queue
from src.services.watermark import process_image

router = Router(name="image_processing")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_MEDIA_GROUP_SIZE = 10  # Ограничение Telegram Bot API на размер медиагруппы
CONCURRENCY_LIMIT = 2     # Ограничение параллельных задач для защиты оперативной памяти (100+ фото)


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


async def update_or_send_queue_card(message: Message, user_id: int, count: int):
    """Отображает обновленный статус очереди всегда в самом низу чата

    и обновляет закрепленную кнопку в поле ввода.
    """
    text = f"📥 <b>В очереди: {count} фото</b>\nНажмите кнопку ниже для старта:"
    inline_kb = get_batch_confirm_kb(count)
    reply_kb = get_batch_reply_kb(count)

    # Удаляем предыдущее сообщение с кнопкой из чата, чтобы оно не висело выше новых фото
    prev_msg_id = batch_queue.get_status_message_id(user_id)
    if prev_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
        except Exception:
            pass

    # Отправляем свежее сообщение в самом низу и активируем нижнюю панель
    new_msg = await message.answer(text, reply_markup=inline_kb, parse_mode="HTML")
    batch_queue.set_status_message(user_id, new_msg.message_id)

    # Обновляем нижнюю панель в Telegram (над полем ввода)
    try:
        await message.answer(
            f"Кнопка запуска обновлена внизу экрана 👇",
            reply_markup=reply_kb,
        )
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

    # 1. Режим «По подтверждению»
    if settings.process_mode == "confirm":
        total_count = batch_queue.add_items(user_id, incoming_items, message.chat.id)
        await update_or_send_queue_card(message, user_id, total_count)
        return

    # 2. Режим «Сразу»: мгновенное подтверждение приема
    status_msg = await message.answer("Фото приняты, обрабатываю...")
    try:
        await process_and_dispatch_items(bot, message.chat.id, user_id, incoming_items)
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
        await update_or_send_queue_card(message, user_id, total_count)
        return

    # Режим «Сразу»: мгновенное уведомление
    status_msg = await message.answer("Файлы приняты, обрабатываю...")
    try:
        await process_and_dispatch_items(bot, message.chat.id, user_id, incoming_items)
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

    # Обработка с контролем прогресса для больших пачек (100+ фото)
    for idx, (file_id, fname) in enumerate(items, 1):
        if status_message and (idx % 10 == 0 or idx == total or total <= 5):
            try:
                await status_message.edit_text(
                    f"⚙️ <b>Обработка: {idx} / {total}</b>...",
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
    """Запуск обработки по нажатию нижней кнопки в поле ввода."""
    user_id = message.from_user.id
    items = batch_queue.pop_all(user_id)

    if not items:
        await message.answer("Очередь пуста.", reply_markup=get_remove_kb())
        return

    status_msg = await message.answer(
        f"⚙️ <b>Обработка: 0 / {len(items)}</b>...",
        parse_mode="HTML",
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
async def handle_reply_batch_clear(message: Message):
    """Очистка очереди по нажатию нижней кнопки."""
    user_id = message.from_user.id
    batch_queue.clear(user_id)
    await message.answer("Очередь очищена.", reply_markup=get_remove_kb())


@router.callback_query(F.data == "batch:start")
async def cb_start_batch(callback: CallbackQuery, bot: Bot):
    """Запуск обработки инлайн-кнопкой."""
    user_id = callback.from_user.id
    items = batch_queue.pop_all(user_id)

    if not items:
        await callback.answer("Очередь пуста.", show_alert=True)
        return

    await callback.answer("Начинаю обработку...")
    status_msg = await callback.message.edit_text(
        f"⚙️ <b>Обработка: 0 / {len(items)}</b>...",
        parse_mode="HTML",
    )
    # Убираем нижнюю панель
    try:
        await callback.message.answer("Запуск...", reply_markup=get_remove_kb())
    except Exception:
        pass

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
        await callback.message.edit_text("Очередь очищена.")
    except Exception:
        pass
    try:
        await callback.message.answer("Очередь очищена.", reply_markup=get_remove_kb())
    except Exception:
        pass
    await callback.answer("Очередь очищена.")
