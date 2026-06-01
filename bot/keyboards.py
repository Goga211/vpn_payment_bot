"""Inline-клавиатуры бота."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import Settings


def main_menu(settings: Settings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Попробовать бесплатно", callback_data="help_connect")
    kb.button(text="👤 Личный кабинет", callback_data="account")
    feedback_url = settings.feedback_url or settings.support_url
    if feedback_url:
        kb.button(text="💬 Отзывы и предложения", url=feedback_url)
    if settings.support_url:
        kb.button(text="🆘 Техподдержка", url=settings.support_url)
    kb.adjust(1)
    return kb.as_markup()


def account_menu(
    settings: Settings,
    *,
    subscription_url: str | None = None,
    found: bool = False,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if found:
        if subscription_url and subscription_url.lower().startswith("http"):
            kb.button(text="🌐 Открыть страницу подписки", url=subscription_url)
        kb.button(text="🔄 Обновить", callback_data="account")
        kb.button(text="🎁 Как подключить", callback_data="help_connect")
    else:
        kb.button(text="🎁 Попробовать бесплатно", callback_data="help_connect")
        kb.button(text="🔄 Обновить", callback_data="account")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="menu")
    return kb.as_markup()
