"""Süreç genelindeki ortam ayarları (veritabanı bağlantısı, log seviyesi vb.)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AWE_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./awe_dev.db"
    log_level: str = "INFO"
    project_config_dir: str = "./config_examples"


@lru_cache
def get_settings() -> Settings:
    return Settings()
