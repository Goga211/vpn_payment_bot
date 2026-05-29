"""Тексты сообщений бота (HTML-разметка Telegram)."""
from __future__ import annotations

import html
from datetime import timezone

from .remnawave import RemnawaveUser

STATUS_LABELS = {
    "ACTIVE": "🟢 активна",
    "EXPIRED": "🔴 истекла",
    "DISABLED": "⚪️ отключена",
    "LIMITED": "🟡 достигнут лимит трафика",
}

LOADING = "⏳ Загружаю данные о подписке…"

SERVICE_UNAVAILABLE = (
    "⚠️ Не удалось получить данные о подписке.\n"
    "Попробуйте ещё раз чуть позже или напишите в поддержку."
)

NOT_CONFIGURED = (
    "⚠️ Личный кабинет временно недоступен — бот ещё настраивается.\n"
    "Загляните немного позже."
)


def welcome(brand: str) -> str:
    return (
        f"👋 Привет! Это бот сервиса <b>{html.escape(brand)}</b>.\n\n"
        "Здесь можно оплатить доступ и получить ссылку на подписку.\n\n"
        "• 💳 <b>Оплатить</b> — откроется страница оплаты прямо в Telegram\n"
        "• 👤 <b>Личный кабинет</b> — ваша ссылка-подписка и срок действия\n"
        "• 📖 <b>Как оплатить</b> — пошаговая инструкция\n"
        "• 🔌 <b>Как подключить</b> — настройка приложения\n\n"
        "Выберите действие 👇"
    )


def how_to_pay() -> str:
    return (
        "📖 <b>Как оплатить</b>\n\n"
        "1️⃣ Нажмите кнопку <b>«💳 Оплатить»</b> в меню — внутри Telegram "
        "откроется страница оплаты.\n"
        "2️⃣ Выберите тариф и оплатите удобным способом.\n"
        "3️⃣ После успешной оплаты доступ создаётся автоматически и "
        "привязывается к вашему Telegram.\n"
        "4️⃣ Вернитесь в бот и откройте <b>«👤 Личный кабинет»</b> — там появится "
        "ваша ссылка-подписка.\n\n"
        "💡 Если оплата прошла, но подписка не появилась за пару минут — "
        "нажмите «🔄 Обновить» в личном кабинете или напишите в поддержку."
    )


def how_to_connect() -> str:
    return (
        "🔌 <b>Как подключиться</b>\n\n"
        "1️⃣ Скопируйте ссылку-подписку из <b>«👤 Личный кабинет»</b> "
        "(нажмите на неё — она скопируется).\n"
        "2️⃣ Установите приложение:\n"
        "   • <b>Android</b> — v2rayTun или Hiddify\n"
        "   • <b>iOS</b> — Streisand, v2rayTun или Hiddify\n"
        "   • <b>Windows / macOS</b> — Hiddify или Nekoray\n"
        "3️⃣ В приложении выберите «Добавить подписку» / «Import from clipboard» "
        "и вставьте ссылку.\n"
        "4️⃣ Обновите подписку и подключайтесь к любому серверу.\n"
    )


def _format_user(user: RemnawaveUser) -> str:
    status = STATUS_LABELS.get(
        user.status, f"❔ {html.escape(user.status or 'неизвестно')}"
    )
    lines = [f"<b>Статус:</b> {status}"]

    if user.username:
        lines.append(f"<b>Логин:</b> <code>{html.escape(user.username)}</code>")

    if user.expire_at:
        date_str = user.expire_at.astimezone(timezone.utc).strftime("%d.%m.%Y")
        days = user.days_left
        if days is not None and days >= 0:
            lines.append(f"<b>Действует до:</b> {date_str} (осталось {days} дн.)")
        else:
            lines.append(f"<b>Действовала до:</b> {date_str} (истекла)")

    if user.subscription_url:
        safe_url = html.escape(user.subscription_url)
        lines.append(f"<b>Ссылка-подписка:</b>\n<code>{safe_url}</code>")

    return "\n".join(lines)


def account(users: list[RemnawaveUser]) -> str:
    if not users:
        return (
            "👤 <b>Личный кабинет</b>\n\n"
            "Активной подписки не найдено.\n"
            "Похоже, вы ещё не оплачивали доступ — или оплата была привязана "
            "к другому Telegram-аккаунту.\n\n"
            "Нажмите <b>«💳 Оплатить»</b>, чтобы оформить доступ."
        )

    if len(users) == 1:
        return "👤 <b>Личный кабинет</b>\n\n" + _format_user(users[0])

    blocks = [f"<b>Подписка {i}</b>\n{_format_user(u)}" for i, u in enumerate(users, 1)]
    return "👤 <b>Личный кабинет</b>\n\n" + "\n\n".join(blocks)
