"""Асинхронный модуль работы с SQLite базой данных и хранилищем логотипов."""

import os
from pathlib import Path
from typing import Optional
import aiosqlite

from src.config import settings
from src.database.models import UserSettings

DEFAULT_LOGO_PATH = Path("assets/default_logo.png")


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self.logos_dir = settings.logos_dir

    async def init(self) -> None:
        """Создает таблицы и директории при старте приложения."""
        self.logos_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    has_custom_logo INTEGER DEFAULT 0,
                    logo_scale TEXT DEFAULT 'medium',
                    logo_opacity INTEGER DEFAULT 100,
                    auto_color INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def get_user_settings(self, user_id: int) -> UserSettings:
        """Получает настройки пользователя, создавая запись по умолчанию, если ее еще нет."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                # Создаем настройки по умолчанию
                await db.execute(
                    """
                    INSERT INTO user_settings (user_id, has_custom_logo, logo_scale, logo_opacity, auto_color)
                    VALUES (?, 0, 'medium', 100, 1)
                    """,
                    (user_id,),
                )
                await db.commit()
                return UserSettings(user_id=user_id)

            return UserSettings(
                user_id=row["user_id"],
                has_custom_logo=bool(row["has_custom_logo"]),
                logo_scale=row["logo_scale"],
                logo_opacity=row["logo_opacity"],
                auto_color=bool(row["auto_color"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_settings(self, user_id: int, **kwargs) -> UserSettings:
        """Обновляет указанные параметры пользователя."""
        allowed_fields = {"has_custom_logo", "logo_scale", "logo_opacity", "auto_color"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return await self.get_user_settings(user_id)

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        insert_cols = ["user_id"] + list(updates.keys())
        placeholders = ", ".join(["?"] * len(insert_cols))
        
        insert_values = [user_id] + list(updates.values())
        update_values = list(updates.values())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                INSERT INTO user_settings ({", ".join(insert_cols)})
                VALUES ({placeholders})
                ON CONFLICT(user_id) DO UPDATE SET
                    {set_clause},
                    updated_at = CURRENT_TIMESTAMP
                """,
                insert_values + update_values,
            )
            await db.commit()

        return await self.get_user_settings(user_id)

    def get_logo_path(self, user_id: int) -> Path:
        """Возвращает путь к кастомному логотипу пользователя."""
        return self.logos_dir / f"{user_id}.png"

    async def has_custom_logo(self, user_id: int) -> bool:
        """Проверяет физическое наличие кастомного логотипа на диске."""
        path = self.get_logo_path(user_id)
        return path.exists() and path.is_file()

    async def save_user_logo(self, user_id: int, logo_bytes: bytes) -> Path:
        """Сохраняет PNG-логотип пользователя на диск и обновляет БД."""
        self.logos_dir.mkdir(parents=True, exist_ok=True)
        logo_path = self.get_logo_path(user_id)

        with open(logo_path, "wb") as f:
            f.write(logo_bytes)

        await self.update_settings(user_id, has_custom_logo=1)
        return logo_path

    async def delete_user_logo(self, user_id: int) -> bool:
        """Удаляет кастомный логотип пользователя."""
        logo_path = self.get_logo_path(user_id)
        deleted = False
        if logo_path.exists():
            try:
                os.remove(logo_path)
                deleted = True
            except OSError:
                pass

        await self.update_settings(user_id, has_custom_logo=0)
        return deleted

    async def get_effective_logo_bytes(self, user_id: int) -> bytes:
        """Возвращает байты кастомного логотипа пользователя или дефолтного водяного знака."""
        custom_path = self.get_logo_path(user_id)
        if custom_path.exists():
            with open(custom_path, "rb") as f:
                return f.read()

        if DEFAULT_LOGO_PATH.exists():
            with open(DEFAULT_LOGO_PATH, "rb") as f:
                return f.read()

        raise FileNotFoundError("Ни кастомный, ни базовый логотип не найдены.")


db = Database()
