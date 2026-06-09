"""Личный кабинет: подтягивает подписку из Remnawave по Telegram ID."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from .. import texts
from ..config import Settings
from ..keyboards import account_menu, back_to_menu, devices_menu
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
    single = len(users) == 1
    # Страницу подписки и устройства показываем только при единственной подписке —
    # тогда однозначно известно, к какому пользователю Remnawave они относятся.
    subscription_url = users[0].subscription_url if single else None
    has_uuid = single and bool(users[0].uuid)

    await safe_edit(
        callback,
        texts.account(users),
        reply_markup=account_menu(
            settings,
            subscription_url=subscription_url,
            found=found,
            show_devices=has_uuid,
        ),
    )


async def _resolve_uuid(
    callback: CallbackQuery, remnawave: RemnawaveClient
) -> str | None:
    """Возвращает UUID единственной подписки пользователя (или None, если её нет/несколько)."""
    users = await remnawave.get_users_by_telegram_id(callback.from_user.id)
    if len(users) == 1 and users[0].uuid:
        return users[0].uuid
    return None


@router.callback_query(F.data == "devices")
async def show_devices(callback: CallbackQuery, remnawave: RemnawaveClient) -> None:
    await callback.answer()

    if not remnawave.enabled:
        await safe_edit(callback, texts.NOT_CONFIGURED, reply_markup=back_to_menu())
        return

    await safe_edit(callback, texts.LOADING)

    try:
        user_uuid = await _resolve_uuid(callback, remnawave)
        if user_uuid is None:
            await safe_edit(callback, texts.devices([]), reply_markup=devices_menu([]))
            return
        devices = await remnawave.get_devices(user_uuid)
    except RemnawaveError as exc:
        logger.warning("Не удалось получить устройства tg=%s: %s", callback.from_user.id, exc)
        await safe_edit(callback, texts.SERVICE_UNAVAILABLE, reply_markup=back_to_menu())
        return

    await safe_edit(callback, texts.devices(devices), reply_markup=devices_menu(devices))


@router.callback_query(F.data.startswith("devdel:"))
async def delete_device(callback: CallbackQuery, remnawave: RemnawaveClient) -> None:
    try:
        index = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    if not remnawave.enabled:
        await callback.answer()
        await safe_edit(callback, texts.NOT_CONFIGURED, reply_markup=back_to_menu())
        return

    try:
        user_uuid = await _resolve_uuid(callback, remnawave)
        devices = await remnawave.get_devices(user_uuid) if user_uuid else []
        # Список могли уже изменить с момента показа — сверяемся по актуальным данным.
        if not (0 <= index < len(devices)):
            await callback.answer("Устройство уже отключено", show_alert=False)
        else:
            await remnawave.delete_device(user_uuid, devices[index].hwid)
            await callback.answer(texts.DEVICE_DELETED, show_alert=False)
            devices = await remnawave.get_devices(user_uuid)
    except RemnawaveError as exc:
        logger.warning("Не удалось удалить устройство tg=%s: %s", callback.from_user.id, exc)
        await callback.answer(texts.DEVICE_DELETE_FAILED, show_alert=True)
        return

    await safe_edit(callback, texts.devices(devices), reply_markup=devices_menu(devices))
