"""Команда /start и возврат в главное меню."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .. import texts
from ..config import Settings
from ..keyboards import main_menu
from ..utils import safe_edit

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, settings: Settings) -> None:
    await message.answer(
        texts.welcome(settings.brand_name),
        reply_markup=main_menu(settings),
    )


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery, settings: Settings) -> None:
    await safe_edit(
        callback,
        texts.welcome(settings.brand_name),
        reply_markup=main_menu(settings),
    )
    await callback.answer()
