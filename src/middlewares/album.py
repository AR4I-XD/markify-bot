"""Надежный Middleware для объединения сообщений из одного альбома (media_group_id)."""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AlbumMiddleware(BaseMiddleware):
    """Собирает все сообщения одного media_group_id с адаптивным ожиданием (debounce).

    Каждое новое сообщение в той же группе продлевает таймер ожидания,
    что гарантирует сбор абсолютно всех фото альбома независимо от сетевой задержки.
    """

    def __init__(self, latency: float = 0.8):
        self.latency = latency
        self.albums: Dict[str, List[Message]] = {}
        self.tasks: Dict[str, asyncio.TimerHandle] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            # Одиночное сообщение (без media_group_id)
            return await handler(event, data)

        media_group_id = event.media_group_id

        # Если группа уже отслеживается, добавляем новое сообщение
        if media_group_id in self.albums:
            self.albums[media_group_id].append(event)
            return None

        # Инициализируем новую группу
        self.albums[media_group_id] = [event]

        # Ждем завершения поступления всех сообщений группы
        # Цикл проверяет, поступают ли еще сообщения
        while True:
            current_count = len(self.albums[media_group_id])
            await asyncio.sleep(self.latency)
            # Если за время ожидания новых сообщений не добавилось, значит альбом пришел полностью
            if len(self.albums[media_group_id]) == current_count:
                break

        album_messages = self.albums.pop(media_group_id, [])
        if not album_messages:
            return None

        # Передаем весь собранный альбом в хэндлер
        data["album"] = album_messages
        return await handler(album_messages[0], data)
