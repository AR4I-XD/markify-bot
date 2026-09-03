"""Сервис автоматической цветокоррекции фотографий."""

from PIL import Image, ImageEnhance, ImageOps


def auto_enhance_image(
    image: Image.Image,
    cutoff: float = 0.5,
    color_factor: float = 1.08,
    contrast_factor: float = 1.05,
    sharpness_factor: float = 1.10,
) -> Image.Image:
    """Интеллектуальная автоцветокоррекция:

    1. Автоматический баланс динамического диапазона (Auto Contrast)
    2. Мягкая оптимизация контрастности
    3. Приятное повышение насыщенности (vibrance)
    4. Легкое повышение детализации (sharpness)

    Работает в цветовом пространстве RGB, сохраняя естественность кадра.
    """
    # Сохраняем альфа-канал, если он есть
    has_alpha = image.mode == "RGBA"
    alpha = None
    if has_alpha:
        alpha = image.getchannel("A")
        rgb_image = image.convert("RGB")
    elif image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image.copy()

    # 1. Автоконтраст с безопасным порогом отсечения шумов в тенях и светах
    # preserve_tone=True сохраняет исходный оттенок без цветового сдвига
    enhanced = ImageOps.autocontrast(rgb_image, cutoff=cutoff, preserve_tone=True)

    # 2. Мягкое улучшение контраста
    if contrast_factor != 1.0:
        contrast_enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = contrast_enhancer.enhance(contrast_factor)

    # 3. Легкое насыщение цветов
    if color_factor != 1.0:
        color_enhancer = ImageEnhance.Color(enhanced)
        enhanced = color_enhancer.enhance(color_factor)

    # 4. Мягкая резкость
    if sharpness_factor != 1.0:
        sharpness_enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = sharpness_enhancer.enhance(sharpness_factor)

    # Возвращаем альфа-канал, если исходник был RGBA
    if has_alpha and alpha is not None:
        enhanced = enhanced.convert("RGBA")
        enhanced.putalpha(alpha)

    return enhanced
