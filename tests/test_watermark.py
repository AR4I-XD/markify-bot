"""Тесты для сервисов наложения водяного знака и автоцветокоррекции."""

import io
import unittest
from PIL import Image

from src.services.color_correction import auto_enhance_image
from src.services.watermark import (
    SCALE_PRESETS,
    compute_logo_dimensions,
    compute_logo_position,
    prepare_logo,
    process_image,
)


class TestWatermarkEngine(unittest.TestCase):
    def setUp(self):
        # Создаем тестовый логотип (прозрачный PNG 200x50 с синей плашкой)
        self.logo = Image.new("RGBA", (200, 50), (0, 0, 0, 0))
        for x in range(200):
            for y in range(50):
                self.logo.putpixel((x, y), (30, 100, 240, 220))

        logo_buf = io.BytesIO()
        self.logo.save(logo_buf, format="PNG")
        self.logo_bytes = logo_buf.getvalue()

    def test_aspect_ratio_preservation(self):
        """Проверка строгого сохранения пропорций логотипа при любых размерах."""
        image_sizes = [
            (3840, 2160),  # 4K горизонтальное
            (1080, 1920),  # Вертикальное (Stories 9:16)
            (1000, 1000),  # Квадратное (1:1)
            (640, 480),    # Небольшое горизонтальное
        ]
        original_aspect = 200 / 50  # 4.0

        for img_sz in image_sizes:
            new_w, new_h = compute_logo_dimensions(img_sz, (200, 50), scale_ratio=0.18)
            computed_aspect = new_w / new_h
            # Пропорции должны сохраняться с точностью до округления пикселей
            self.assertAlmostEqual(computed_aspect, original_aspect, delta=0.15)

    def test_logo_position_bottom_right(self):
        """Проверка, что логотип строго размещается в правом нижнем углу с безопасным отступом."""
        test_cases = [
            ((3840, 2160), (300, 75)),
            ((1080, 1920), (190, 47)),
            ((800, 800), (140, 35)),
        ]

        for img_size, logo_size in test_cases:
            img_w, img_h = img_size
            logo_w, logo_h = logo_size
            pos_x, pos_y = compute_logo_position(img_size, logo_size)

            # Должен быть в правом нижнем углу
            self.assertGreater(pos_x, img_w / 2)
            self.assertGreater(pos_y, img_h / 2)

            # Не должен выходить за пределы изображения
            self.assertLessEqual(pos_x + logo_w, img_w)
            self.assertLessEqual(pos_y + logo_h, img_h)

    def test_color_correction_rgb_and_rgba(self):
        """Проверка автоцветокоррекции для RGB и RGBA форматов."""
        rgb_img = Image.new("RGB", (300, 200), (120, 130, 140))
        enhanced_rgb = auto_enhance_image(rgb_img)
        self.assertEqual(enhanced_rgb.size, (300, 200))
        self.assertEqual(enhanced_rgb.mode, "RGB")

        rgba_img = Image.new("RGBA", (300, 200), (120, 130, 140, 200))
        enhanced_rgba = auto_enhance_image(rgba_img)
        self.assertEqual(enhanced_rgba.size, (300, 200))
        self.assertEqual(enhanced_rgba.mode, "RGBA")

    def test_process_image_in_memory_zero_storage(self):
        """Комплексный тест пайплайна: фото обрабатывается полностью в памяти (zero-storage)."""
        formats_to_test = [
            ((1920, 1080), "horizontal"),
            ((1080, 1920), "vertical"),
            ((1000, 1000), "square"),
        ]

        for size, label in formats_to_test:
            with self.subTest(label=label):
                # Исходное тестовое изображение
                orig_img = Image.new("RGB", size, (180, 200, 220))
                img_buf = io.BytesIO()
                orig_img.save(img_buf, format="JPEG")
                orig_bytes = img_buf.getvalue()

                # Обработка с логотипом и автоцветокоррекцией
                result_buf = process_image(
                    image_input=orig_bytes,
                    logo_input=self.logo_bytes,
                    auto_color=True,
                    scale="medium",
                    opacity=90,
                )

                # Проверка результата
                self.assertIsInstance(result_buf, io.BytesIO)
                self.assertGreater(result_buf.getbuffer().nbytes, 0)

                # Загружаем полученное изображение для верификации
                result_img = Image.open(result_buf)
                self.assertEqual(result_img.size, size)

    def test_exif_orientation_handling(self):
        """Проверка корректной обработки фото с EXIF тегом ориентации (характерно для смартфонов)."""
        img = Image.new("RGB", (800, 600), (200, 100, 50))
        # Создаем изображение с EXIF orientation 6 (повернуто на 90 градусов по часовой стрелке)
        exif = img.getexif()
        exif[0x0112] = 6  # EXIF Orientation tag
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        
        result_buf = process_image(
            image_input=buf.getvalue(),
            logo_input=self.logo_bytes,
            auto_color=False,
        )
        result_img = Image.open(result_buf)
        # После exif_transpose изображение 800x600 с ориентацией 6 транспонируется в 600x800
        self.assertEqual(result_img.size, (600, 800))


if __name__ == "__main__":
    unittest.main()
