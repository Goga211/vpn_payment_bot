"""Инструкции: как оплатить и как подключиться."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from .. import texts
from ..keyboards import back_to_menu
from ..utils import safe_edit

router = Router(name="help")


@router.callback_query(F.data == "help_pay")
async def help_pay(callback: CallbackQuery) -> None:
    await safe_edit(callback, texts.how_to_pay(), reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "help_connect")
async def help_connect(callback: CallbackQuery) -> None:
    await safe_edit(callback, texts.how_to_connect(), reply_markup=back_to_menu())
    await callback.answer()
