"""Личный кабинет: подтягивает подписку из Remnawave по Telegram ID."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from .. import texts
from ..config import Settings
from ..keyboards import account_menu, back_to_menu
from ..remnawave import RemnawaveClient, RemnawaveError
from ..utils import safe_edit

router = Router(name="account")
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "account")
async def show_account(
    callback: CallbackQuery,
    settings: Settings,
    remnawave: RemnawaveClient,
) -> None:
    await callback.answer()

    if not remnawave.enabled:
        await safe_edit(callback, texts.NOT_CONFIGURED, reply_markup=back_to_menu())
        return

    await safe_edit(callback, texts.LOADING)

    try:
        users = await remnawave.get_users_by_telegram_id(callback.from_user.id)
    except RemnawaveError as exc:
        logger.warning(
            "Remnawave lookup failed for telegram_id=%s: %s",
            callback.from_user.id,
            exc,
        )
        await safe_edit(callback, texts.SERVICE_UNAVAILABLE, reply_markup=back_to_menu())
        return

    found = bool(users)
    # Кнопку «Открыть страницу подписки» показываем только при единственной подписке.
    subscription_url = users[0].subscription_url if len(users) == 1 else None

    await safe_edit(
        callback,
        texts.account(users),
        reply_markup=account_menu(
            settings,
            subscription_url=subscription_url,
            found=found,
        ),
    )
