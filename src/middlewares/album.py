"""Middleware для объединения сообщений из одного альбома (media_group_id)."""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.albums: Dict[str, List[Message]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            # Одиночное сообщение
            return await handler(event, data)

        media_group_id = event.media_group_id

        # Если этот альбом уже начал собираться, просто добавляем сообщение
        if media_group_id in self.albums:
            self.albums[media_group_id].append(event)
            return None

        # Инициализируем сбор сообщений альбома
        self.albums[media_group_id] = [event]

        # Ждем поступления всех элементов альбома от Telegram
        await asyncio.sleep(self.latency)

        album_messages = self.albums.pop(media_group_id, [])
        if not album_messages:
            return None

        # Передаем список сообщений альбома в хэндлер
        data["album"] = album_messages
        return await handler(album_messages[0], data)
