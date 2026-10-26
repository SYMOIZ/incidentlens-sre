"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INCIDENTLENS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = "incidentlens.db"
    error_repeat_threshold: int = Field(default=3, ge=1)
    error_window_seconds: int = Field(default=300, ge=1)
    baseline_multiplier: float = Field(default=3.0, gt=1.0)
    baseline_min_samples: int = Field(default=20, ge=1)
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
