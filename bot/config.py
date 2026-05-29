"""Конфигурация бота. Значения берутся из переменных окружения и/или файла .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str = Field(alias="BOT_TOKEN")

    # Remnawave
    remnawave_base_url: str = Field(default="", alias="REMNAWAVE_BASE_URL")
    remnawave_token: str = Field(default="", alias="REMNAWAVE_TOKEN")
    remnawave_username: str = Field(default="", alias="REMNAWAVE_USERNAME")
    remnawave_password: str = Field(default="", alias="REMNAWAVE_PASSWORD")
    remnawave_timeout: float = Field(default=12.0, alias="REMNAWAVE_TIMEOUT")

    # Прочее
    payment_url: str = Field(default="https://aiyl-bank.ru/checkout", alias="PAYMENT_URL")
    support_url: str = Field(default="", alias="SUPPORT_URL")
    brand_name: str = Field(default="Nimbus", alias="BRAND_NAME")

    @field_validator("remnawave_base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        value = (value or "").strip().rstrip("/")
        # panel.example.com — это плейсхолдер из .env.example, считаем его «не задано».
        if "example.com" in value:
            return ""
        return value

    @field_validator("payment_url", "support_url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return (value or "").strip()

    @property
    def remnawave_enabled(self) -> bool:
        """Сконфигурирован ли доступ к панели (есть URL и способ авторизации)."""
        if not self.remnawave_base_url:
            return False
        if self.remnawave_token:
            return True
        return bool(self.remnawave_username and self.remnawave_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
