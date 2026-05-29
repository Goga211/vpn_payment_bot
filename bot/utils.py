"""Вспомогательные функции для обработчиков."""
from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def safe_edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    disable_web_page_preview: bool = True,
) -> None:
    """Редактирует сообщение под кнопкой; если нельзя — отправляет новое.

    Гасит TelegramBadRequest вроде «message is not modified» (повторное нажатие
    той же кнопки) и случаи, когда исходное сообщение нельзя редактировать.
    """
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        try:
            await callback.message.answer(
                text,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        except TelegramBadRequest:
            pass
