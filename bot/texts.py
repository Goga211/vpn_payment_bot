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
        "🇰🇬 <b>Платежный сервер (Кыргызстан)</b>\n"
        "Ваш личный сервер для бесперебойных оплат и интернета.\n\n"
        "🔥 <b>Почему он нужен:</b>\n"
        "1️⃣ <b>Гарантия оплат:</b> Платежные системы видят вас внутри "
        "Кыргызстана. Карты МБАНК работают на 100%, без ложных блокировок "
        "со стороны систем безопасности + экономите на НДС.\n"
        "2️⃣ <b>Стабильный доступ:</b> Обеспечьте бесперебойное подключение к "
        "международным рабочим сервисам, корпоративным сайтам, подпискам и "
        "мессенджерам без сбоев и потери скорости.\n\n"
        "🔥 <b>Тестовый режим: 1 месяц — БЕСПЛАТНО!</b> Чтобы вы лично "
        "убедились в стабильности сервера. Нам важно ваше мнение! Напишите "
        "нам отзыв или предложение по работе сервера.\n\n"
        "<b>ВЫБЕРИТЕ ДЕЙСТВИЕ</b>👇\n"
        "🎁 <b>Попробовать бесплатно</b> — как подключить\n"
        "👤 <b>Личный кабинет</b> — подписка и срок действия\n"
        "💬 <b>Отзывы и предложения</b> — напишите нам\n"
        "🆘 <b>Техподдержка</b> — если что-то не работает"
    )


def how_to_connect() -> str:
    return (
        "🎁 <b>Попробовать бесплатно</b>\n\n"
        "Тестовый месяц подключается бесплатно — выполните пару шагов:\n\n"
        "1️⃣ Скопируйте ссылку-подписку из <b>«👤 Личный кабинет»</b> "
        "(нажмите на неё — она скопируется).\n"
        "2️⃣ Установите приложение:\n"
        "   • <b>Android</b> — v2rayTun или Hiddify\n"
        "   • <b>iOS</b> — Streisand, v2rayTun или Hiddify\n"
        "   • <b>Windows / macOS</b> — Hiddify или Nekoray\n"
        "3️⃣ В приложении выберите «Добавить подписку» / «Import from clipboard» "
        "и вставьте ссылку.\n"
        "4️⃣ Обновите подписку и подключайтесь к серверу.\n"
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
            "Похоже, доступ ещё не оформлен — или он был привязан "
            "к другому Telegram-аккаунту.\n\n"
            "Нажмите <b>«🎁 Попробовать бесплатно»</b>, чтобы подключиться."
        )

    if len(users) == 1:
        return "👤 <b>Личный кабинет</b>\n\n" + _format_user(users[0])

    blocks = [f"<b>Подписка {i}</b>\n{_format_user(u)}" for i, u in enumerate(users, 1)]
    return "👤 <b>Личный кабинет</b>\n\n" + "\n\n".join(blocks)
