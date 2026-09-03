from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения, считываемая из переменных окружения или .env."""
    BOT_TOKEN: str = "placeholder_token"
    DATA_DIR: Path = Path("data")
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def logos_dir(self) -> Path:
        return self.DATA_DIR / "logos"

    @property
    def db_path(self) -> Path:
        return self.DATA_DIR / "markify.db"


settings = Settings()
