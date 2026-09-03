"""Тесты для менеджера очереди пакетной обработки batch_queue."""

import unittest
from src.services.batch_queue import BatchQueueManager


class TestBatchQueue(unittest.TestCase):
    def setUp(self):
        self.queue_mgr = BatchQueueManager()

    def test_add_and_pop_items(self):
        """Проверка накопления элементов в очереди и их извлечения."""
        user_id = 123
        chat_id = 456

        count = self.queue_mgr.add_items(user_id, [("file1", "p1.jpg"), ("file2", "p2.jpg")], chat_id)
        self.assertEqual(count, 2)

        count = self.queue_mgr.add_items(user_id, [("file3", "p3.jpg")], chat_id)
        self.assertEqual(count, 3)

        items = self.queue_mgr.pop_all(user_id)
        self.assertEqual(len(items), 3)
        self.assertEqual(self.queue_mgr.get_count(user_id), 0)

    def test_clear_queue(self):
        """Проверка очистки очереди."""
        user_id = 999
        self.queue_mgr.add_items(user_id, [("f1", "1.jpg")], chat_id=1)
        self.assertEqual(self.queue_mgr.get_count(user_id), 1)

        self.queue_mgr.clear(user_id)
        self.assertEqual(self.queue_mgr.get_count(user_id), 0)


if __name__ == "__main__":
    unittest.main()
