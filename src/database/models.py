"""Модели данных настроек пользователя."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserSettings:
    user_id: int
    has_custom_logo: bool = False
    logo_scale: str = "medium"  # "small" | "medium" | "large"
    logo_opacity: int = 100      # 50..100
    auto_color: bool = True      # True | False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
