"""Тесты для проверки корректности компонентов и форматирования UI."""

import unittest
from src.database.models import UserSettings
from src.handlers.common import format_welcome_text, format_help_text
from src.handlers.settings import format_settings_text
from src.handlers.image import format_progress_text
from src.keyboards.inline import (
    POSITION_NAMES,
    SCALE_NAMES,
    get_main_menu_kb,
    get_settings_kb,
    get_preview_nav_kb,
    get_help_kb,
)
from src.keyboards.reply import get_batch_reply_kb, get_remove_kb


class TestUI(unittest.TestCase):
    def setUp(self):
        self.default_settings = UserSettings(
            user_id=12345,
            has_custom_logo=False,
            logo_scale="medium",
            logo_opacity=100,
            logo_position="bottom_right",
            process_mode="auto",
            auto_color=True,
        )
        self.custom_settings = UserSettings(
            user_id=67890,
            has_custom_logo=True,
            logo_scale="large",
            logo_opacity=80,
            logo_position="top_left",
            process_mode="confirm",
            auto_color=False,
        )

    def test_format_welcome_text(self):
        text_def = format_welcome_text(self.default_settings)
        self.assertIn("Markify", text_def)
        self.assertIn("Стандартный", text_def)
        self.assertIn("⚡ Сразу", text_def)
        self.assertIn("Вкл", text_def)

        text_cust = format_welcome_text(self.custom_settings)
        self.assertIn("Пользовательский", text_cust)
        self.assertIn("⏳ По кнопке", text_cust)
        self.assertIn("Выкл", text_cust)

    def test_format_help_text(self):
        help_text = format_help_text()
        self.assertIn("Справка и возможности Markify", help_text)
        self.assertIn("⚡ Сразу", help_text)
        self.assertIn("⏳ По кнопке", help_text)

    def test_format_settings_text(self):
        text = format_settings_text(self.default_settings)
        self.assertIn("Параметры брендирования", text)
        self.assertIn("⚡ Сразу при отправке", text)
        self.assertIn("↘️ Снизу справа", text)
        self.assertIn("18% (Стандарт)", text)
        self.assertIn("100%", text)
        self.assertIn("Включена", text)

    def test_format_progress_text(self):
        single = format_progress_text(1, 1)
        self.assertEqual(single, "⚡ <b>Обработка фото...</b>")

        batch = format_progress_text(5, 10)
        self.assertIn("5 из 10 фото", batch)
        self.assertIn("50%", batch)
        self.assertIn("▰", batch)
        self.assertIn("▱", batch)

    def test_keyboards_structure(self):
        main_kb = get_main_menu_kb()
        self.assertEqual(len(main_kb.inline_keyboard), 2)

        settings_kb = get_settings_kb(self.default_settings)
        # Verify no custom logo reset button
        buttons_text = [b.text for row in settings_kb.inline_keyboard for b in row]
        self.assertFalse(any("Сбросить логотип" in t for t in buttons_text))

        settings_kb_cust = get_settings_kb(self.custom_settings)
        buttons_text_cust = [b.text for row in settings_kb_cust.inline_keyboard for b in row]
        self.assertTrue(any("Сбросить логотип" in t for t in buttons_text_cust))

        preview_nav = get_preview_nav_kb()
        p_texts = [b.text for row in preview_nav.inline_keyboard for b in row]
        self.assertIn("⚙️ Настройки", p_texts)
        self.assertIn("🏠 В главное меню", p_texts)

        help_nav = get_help_kb()
        h_texts = [b.text for row in help_nav.inline_keyboard for b in row]
        self.assertIn("⚙️ Настройки", h_texts)
        self.assertIn("🏠 В главное меню", h_texts)

    def test_reply_keyboard_placeholder(self):
        reply_kb = get_batch_reply_kb(42)
        self.assertEqual(reply_kb.keyboard[0][0].text, "🚀 Обработать (42 фото)")
        self.assertEqual(reply_kb.input_field_placeholder, "Нажмите «🚀 Обработать» для запуска...")


if __name__ == "__main__":
    unittest.main()
