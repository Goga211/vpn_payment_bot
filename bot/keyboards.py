"""Inline-клавиатуры бота."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import Settings


def _pay_button_kwargs(url: str) -> dict:
    """Кнопка оплаты: web_app для HTTPS (открывается внутри Telegram), иначе обычная ссылка.

    Telegram разрешает WebApp-кнопки только для HTTPS-URL, поэтому для не-HTTPS
    (например, локального теста) откатываемся на обычную url-кнопку.
    """
    if url.lower().startswith("https://"):
        return {"web_app": WebAppInfo(url=url)}
    return {"url": url}


def main_menu(settings: Settings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить", **_pay_button_kwargs(settings.payment_url))
    kb.button(text="👤 Личный кабинет", callback_data="account")
    kb.button(text="📖 Как оплатить", callback_data="help_pay")
    kb.button(text="🔌 Как подключить", callback_data="help_connect")
    if settings.support_url:
        kb.button(text="🆘 Поддержка", url=settings.support_url)
    # Раскладка: оплата / кабинет / две подсказки рядом / поддержка
    kb.adjust(1, 1, 2, 1)
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
        kb.button(text="🔌 Как подключить", callback_data="help_connect")
    else:
        kb.button(text="💳 Оплатить", **_pay_button_kwargs(settings.payment_url))
        kb.button(text="🔄 Обновить", callback_data="account")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="menu")
    return kb.as_markup()
