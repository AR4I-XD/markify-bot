"""Тесты для модуля базы данных и управления настройками пользователей."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.database.db import Database


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self.database = Database(db_path=self.db_path)
        self.database.logos_dir = Path(self.test_dir) / "logos"
        await self.database.init()

    async def asyncTearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_get_default_settings(self):
        """Проверка генерации настроек по умолчанию для нового пользователя."""
        settings = await self.database.get_user_settings(user_id=12345)
        self.assertEqual(settings.user_id, 12345)
        self.assertFalse(settings.has_custom_logo)
        self.assertEqual(settings.logo_scale, "medium")
        self.assertEqual(settings.logo_opacity, 100)
        self.assertEqual(settings.logo_position, "bottom_right")
        self.assertTrue(settings.auto_color)

    async def test_update_settings(self):
        """Проверка изменения отдельных настроек (масштаб, угол, автоцветокор)."""
        await self.database.get_user_settings(user_id=54321)

        updated = await self.database.update_settings(
            user_id=54321,
            auto_color=False,
            logo_scale="large",
            logo_opacity=80,
            logo_position="top_left",
        )
        self.assertFalse(updated.auto_color)
        self.assertEqual(updated.logo_scale, "large")
        self.assertEqual(updated.logo_opacity, 80)
        self.assertEqual(updated.logo_position, "top_left")

        # Проверка повторного чтения из БД
        reloaded = await self.database.get_user_settings(user_id=54321)
        self.assertFalse(reloaded.auto_color)
        self.assertEqual(reloaded.logo_position, "top_left")

    async def test_save_and_delete_logo(self):
        """Проверка сохранения и удаления кастомного логотипа пользователя."""
        dummy_logo = b"fake_png_data_123"
        logo_path = await self.database.save_user_logo(user_id=999, logo_bytes=dummy_logo)
        self.assertTrue(logo_path.exists())

        has_logo = await self.database.has_custom_logo(user_id=999)
        self.assertTrue(has_logo)

        # Удаление
        deleted = await self.database.delete_user_logo(user_id=999)
        self.assertTrue(deleted)
        self.assertFalse(await self.database.has_custom_logo(user_id=999))


if __name__ == "__main__":
    unittest.main()
