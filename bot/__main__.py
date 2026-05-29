"""Точка входа: python -m bot"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from pydantic import ValidationError

from .config import Settings, get_settings
from .handlers import account, help as help_handlers, start
from .remnawave import RemnawaveClient

logger = logging.getLogger(__name__)


def _build_remnawave(settings: Settings) -> RemnawaveClient:
    return RemnawaveClient(
        settings.remnawave_base_url,
        token=settings.remnawave_token,
        username=settings.remnawave_username,
        password=settings.remnawave_password,
        timeout=settings.remnawave_timeout,
    )


async def run(settings: Settings) -> None:
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    remnawave = _build_remnawave(settings)

    # Прокидываем зависимости в обработчики через workflow data (aiogram сопоставляет по имени).
    dp["settings"] = settings
    dp["remnawave"] = remnawave

    dp.include_router(start.router)
    dp.include_router(account.router)
    dp.include_router(help_handlers.router)

    if settings.remnawave_enabled:
        logger.info("Remnawave: %s", settings.remnawave_base_url)
    else:
        logger.warning(
            "Remnawave не настроен — личный кабинет будет недоступен "
            "(заполните REMNAWAVE_* в .env)."
        )
    logger.info("Страница оплаты (Mini App): %s", settings.payment_url)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await remnawave.aclose()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = get_settings()
    except ValidationError:
        logger.error(
            "Не задан BOT_TOKEN (или другие обязательные переменные). "
            "Скопируйте .env.example в .env и заполните значения."
        )
        raise SystemExit(1)

    try:
        asyncio.run(run(settings))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота.")


if __name__ == "__main__":
    main()
