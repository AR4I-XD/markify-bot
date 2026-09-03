"""Сервис адаптивного наложения водяного знака (логотипа) и обработки изображений."""

import io
from typing import Literal, Optional, Tuple, Union
from PIL import Image, ImageEnhance, ImageOps

from src.services.color_correction import auto_enhance_image

# Предустановки относительного размера логотипа (доля от меньшей стороны фото)
SCALE_PRESETS = {
    "small": 0.14,
    "medium": 0.18,
    "large": 0.25,
}

LogoScale = Literal["small", "medium", "large"]


def compute_logo_dimensions(
    image_size: Tuple[int, int],
    logo_size: Tuple[int, int],
    scale_ratio: float = 0.18,
) -> Tuple[int, int]:
    """Вычисляет целевой размер логотипа с сохранением его пропорций.

    Размер рассчитывается относительно меньшей стороны исходного фото (min(w, h)),
    что гарантирует визуальную одинаковость логотипа на фото любого формата
    (вертикальные 9:16, горизонтальные 16:9, квадратные 1:1) и любого разрешения (от 500px до 4K+).
    """
    img_w, img_h = image_size
    logo_w, logo_h = logo_size

    min_dim = min(img_w, img_h)
    target_box = max(24, int(min_dim * scale_ratio))

    aspect_ratio = logo_w / logo_h

    if logo_w >= logo_h:
        new_w = target_box
        new_h = max(1, int(target_box / aspect_ratio))
    else:
        new_h = target_box
        new_w = max(1, int(target_box * aspect_ratio))

    return new_w, new_h


def compute_logo_position(
    image_size: Tuple[int, int],
    logo_size: Tuple[int, int],
    padding_ratio: float = 0.025,
    min_padding: int = 12,
) -> Tuple[int, int]:
    """Вычисляет координаты (x, y) для размещения логотипа в правом нижнем углу.

    Отступ (padding) также рассчитывается адаптивно от размера кадра.
    """
    img_w, img_h = image_size
    logo_w, logo_h = logo_size

    min_dim = min(img_w, img_h)
    padding = max(min_padding, int(min_dim * padding_ratio))

    pos_x = img_w - logo_w - padding
    pos_y = img_h - logo_h - padding

    # Страховка от выхода за границы на очень узких/маленьких изображениях
    pos_x = max(0, pos_x)
    pos_y = max(0, pos_y)

    return pos_x, pos_y


def prepare_logo(
    logo_img: Image.Image,
    target_size: Tuple[int, int],
    opacity: int = 100,
) -> Image.Image:
    """Масштабирует логотип до целевого размера и применяет прозрачность.

    Гарантирует формат RGBA с альфа-каналом.
    """
    logo = logo_img.convert("RGBA")
    logo = logo.resize(target_size, resample=Image.Resampling.LANCZOS)

    # Применение прозрачности (0..100)
    if opacity < 100:
        r, g, b, a = logo.split()
        alpha_factor = max(0.0, min(1.0, opacity / 100.0))
        a = ImageEnhance.Brightness(a).enhance(alpha_factor)
        logo = Image.merge("RGBA", (r, g, b, a))

    return logo


def process_image(
    image_input: Union[bytes, io.BytesIO],
    logo_input: Union[bytes, io.BytesIO, Image.Image],
    auto_color: bool = True,
    scale: Union[LogoScale, float] = "medium",
    opacity: int = 100,
    output_format: Optional[str] = None,
) -> io.BytesIO:
    """Главный пайплайн обработки изображения (Zero-Storage, все вычисления в памяти):

    1. Загрузка исходного фото и логотипа из потоков байт.
    2. Коррекция EXIF-ориентации (предотвращает переворот фото с телефонов).
    3. Автоцветокоррекция (если включена).
    4. Адаптивное масштабирование логотипа и расчет координат правого нижнего угла.
    5. Наложение логотипа через альфа-композитинг.
    6. Экспорт в BytesIO с сохранением максимального качества.
    """
    # 1. Открытие фото
    if isinstance(image_input, bytes):
        img_buffer = io.BytesIO(image_input)
    else:
        img_buffer = image_input

    base_image = Image.open(img_buffer)
    # Коррекция ориентации на основе EXIF
    base_image = ImageOps.exif_transpose(base_image) or base_image

    original_format = (base_image.format or "JPEG").upper()
    if output_format is None:
        # Если исходник PNG с прозрачностью, сохраняем как PNG, иначе JPEG
        if base_image.mode in ("RGBA", "LA") or (base_image.mode == "P" and "transparency" in base_image.info):
            out_fmt = "PNG"
        else:
            out_fmt = "JPEG"
    else:
        out_fmt = output_format.upper()

    # 2. Автоцветокоррекция
    if auto_color:
        base_image = auto_enhance_image(base_image)

    # 3. Открытие логотипа
    if isinstance(logo_input, Image.Image):
        logo_image = logo_input
    elif isinstance(logo_input, bytes):
        logo_image = Image.open(io.BytesIO(logo_input))
    else:
        logo_image = Image.open(logo_input)

    # 4. Определение коэффициента масштабирования
    if isinstance(scale, str):
        scale_ratio = SCALE_PRESETS.get(scale, SCALE_PRESETS["medium"])
    else:
        scale_ratio = float(scale)

    # 5. Расчет адаптивного размера и координат
    target_logo_size = compute_logo_dimensions(base_image.size, logo_image.size, scale_ratio)
    pos_x, pos_y = compute_logo_position(base_image.size, target_logo_size)

    # 6. Подготовка логотипа
    prepared_logo = prepare_logo(logo_image, target_logo_size, opacity)

    # 7. Композитинг: наложение логотипа на базовое фото
    # Преобразуем базовое фото в RGBA для наложения прозрачного логотипа
    if base_image.mode != "RGBA":
        composite = base_image.convert("RGBA")
    else:
        composite = base_image.copy()

    # Создаем оверлей того же размера, что и изображение
    overlay = Image.new("RGBA", composite.size, (0, 0, 0, 0))
    overlay.paste(prepared_logo, (pos_x, pos_y), prepared_logo)

    # Безопасное наложение с сохранением альфа-каналов
    result_rgba = Image.alpha_composite(composite, overlay)

    # 8. Экспорт в буфер памяти
    output_buffer = io.BytesIO()
    if out_fmt == "JPEG":
        result_final = result_rgba.convert("RGB")
        result_final.save(output_buffer, format="JPEG", quality=95, subsampling=0, optimize=True)
    elif out_fmt == "PNG":
        result_rgba.save(output_buffer, format="PNG", optimize=True)
    elif out_fmt == "WEBP":
        result_rgba.save(output_buffer, format="WEBP", quality=95)
    else:
        result_final = result_rgba.convert("RGB")
        result_final.save(output_buffer, format="JPEG", quality=95)

    output_buffer.seek(0)
    return output_buffer
