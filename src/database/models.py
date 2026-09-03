"""Модели данных настроек пользователя."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserSettings:
    user_id: int
    has_custom_logo: bool = False
    logo_scale: str = "medium"          # "small" | "medium" | "large"
    logo_opacity: int = 100             # 50..100
    logo_position: str = "bottom_right" # "bottom_right" | "bottom_left" | "top_right" | "top_left"
    process_mode: str = "auto"          # "auto" (сразу) | "confirm" (по кнопке)
    auto_color: bool = True             # True | False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
