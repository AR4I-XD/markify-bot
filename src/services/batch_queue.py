"""Менеджер очереди пакетной обработки (по подтверждению) и оптимизация памяти."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class UserQueue:
    items: List[Tuple[str, str]] = field(default_factory=list)  # [(file_id, filename), ...]
    status_message_id: Optional[int] = None
    chat_id: Optional[int] = None


class BatchQueueManager:
    def __init__(self):
        self._queues: Dict[int, UserQueue] = {}

    def get_queue(self, user_id: int) -> UserQueue:
        if user_id not in self._queues:
            self._queues[user_id] = UserQueue()
        return self._queues[user_id]

    def add_items(self, user_id: int, items: List[Tuple[str, str]], chat_id: int) -> int:
        """Добавляет файлы в очередь пользователя и возвращает текущее количество."""
        queue = self.get_queue(user_id)
        queue.chat_id = chat_id
        queue.items.extend(items)
        return len(queue.items)

    def get_count(self, user_id: int) -> int:
        return len(self.get_queue(user_id).items)

    def pop_all(self, user_id: int) -> List[Tuple[str, str]]:
        queue = self.get_queue(user_id)
        items = list(queue.items)
        queue.items.clear()
        queue.status_message_id = None
        return items

    def clear(self, user_id: int) -> None:
        queue = self.get_queue(user_id)
        queue.items.clear()
        queue.status_message_id = None

    def set_status_message(self, user_id: int, message_id: int) -> None:
        self.get_queue(user_id).status_message_id = message_id

    def get_status_message_id(self, user_id: int) -> Optional[int]:
        return self.get_queue(user_id).status_message_id


batch_queue = BatchQueueManager()
