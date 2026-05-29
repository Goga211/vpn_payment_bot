"""Тонкий async-клиент к API панели Remnawave.

Повторяет проверенную логику Go-бэка сайта:
* авторизация статичным Bearer-токеном ЛИБО логином/паролем (POST /api/auth/login);
* при 401 с парольной авторизацией — один повторный логин;
* все ответы обёрнуты в {"response": ...}.

Боту нужен только один запрос — получить пользователя(ей) по Telegram ID.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Обрезает доли секунды до 6 знаков: datetime.fromisoformat не понимает наносекунды.
_SUBSECOND_RE = re.compile(r"(\.\d{6})\d+")


class RemnawaveError(Exception):
    """Базовая ошибка взаимодействия с Remnawave."""


class RemnawaveNotConfigured(RemnawaveError):
    """Доступ к панели не настроен."""


class RemnawaveAuthError(RemnawaveError):
    """Не удалось авторизоваться в панели."""


def _parse_iso(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    text = _SUBSECOND_RE.sub(r"\1", text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        logger.warning("Не удалось разобрать дату: %r", value)
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@dataclass(slots=True)
class RemnawaveUser:
    uuid: str = ""
    short_uuid: str = ""
    username: str = ""
    status: str = ""
    expire_at: datetime | None = None
    subscription_url: str = ""
    used_traffic_bytes: int = 0
    traffic_limit_bytes: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemnawaveUser":
        return cls(
            uuid=str(data.get("uuid") or ""),
            short_uuid=str(data.get("shortUuid") or ""),
            username=str(data.get("username") or ""),
            status=str(data.get("status") or "").upper(),
            expire_at=_parse_iso(data.get("expireAt")),
            subscription_url=str(data.get("subscriptionUrl") or ""),
            used_traffic_bytes=_as_int(data.get("usedTrafficBytes")),
            traffic_limit_bytes=_as_int(data.get("trafficLimitBytes")),
        )

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def days_left(self) -> int | None:
        """Сколько целых дней осталось до окончания (отрицательное — уже истекла)."""
        if self.expire_at is None:
            return None
        delta = self.expire_at - datetime.now(timezone.utc)
        return int(delta.total_seconds() // 86400)


def _extract_users(payload: Any) -> list[RemnawaveUser]:
    """Достаёт список пользователей из ответа, устойчиво к форме (list / dict / {users:[]})."""
    response = payload.get("response", payload) if isinstance(payload, dict) else payload

    if isinstance(response, list):
        items = response
    elif isinstance(response, dict):
        if isinstance(response.get("users"), list):
            items = response["users"]
        else:
            items = [response]
    else:
        items = []

    return [RemnawaveUser.from_dict(item) for item in items if isinstance(item, dict)]


class RemnawaveClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: str = "",
        username: str = "",
        password: str = "",
        timeout: float = 12.0,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._token = (token or "").strip()
        self._has_static_token = bool(self._token)
        self._username = (username or "").strip()
        self._password = (password or "").strip()
        self._auth_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    @property
    def enabled(self) -> bool:
        if not self._base_url:
            return False
        if self._token or self._has_static_token:
            return True
        return bool(self._username and self._password)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_users_by_telegram_id(self, telegram_id: int | str) -> list[RemnawaveUser]:
        """Возвращает подписки, привязанные к Telegram ID (пустой список — ничего не найдено)."""
        payload = await self._request("GET", f"/api/users/by-telegram-id/{telegram_id}")
        if payload is None:
            return []
        return _extract_users(payload)

    # --- внутреннее ---

    async def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        if not self.enabled:
            raise RemnawaveNotConfigured("Доступ к Remnawave не настроен")

        token = await self._get_token()
        response = await self._do(method, path, token, json)

        # Токен протух — перелогиниваемся один раз (только при парольной авторизации).
        if response.status_code == 401 and not self._has_static_token and self._username:
            async with self._auth_lock:
                self._token = ""
            token = await self._get_token()
            response = await self._do(method, path, token, json)

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise RemnawaveError(
                f"{method} {path} -> {response.status_code}: {response.text[:200]}"
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:  # пришёл не-JSON
            raise RemnawaveError(f"{method} {path}: некорректный JSON в ответе") from exc

    async def _do(
        self, method: str, path: str, token: str, json: Any
    ) -> httpx.Response:
        try:
            return await self._client.request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            raise RemnawaveError(f"Сетевая ошибка при запросе {method} {path}: {exc}") from exc

    async def _get_token(self) -> str:
        async with self._auth_lock:
            if self._token:
                return self._token
            if not (self._username and self._password):
                raise RemnawaveNotConfigured("Нет токена и логина/пароля для Remnawave")
            try:
                response = await self._client.post(
                    "/api/auth/login",
                    json={"username": self._username, "password": self._password},
                )
            except httpx.HTTPError as exc:
                raise RemnawaveAuthError(f"Сетевая ошибка при логине: {exc}") from exc

            if response.status_code >= 400:
                raise RemnawaveAuthError(
                    f"Логин не удался: {response.status_code} {response.text[:200]}"
                )
            data = response.json()
            token = ""
            if isinstance(data, dict):
                resp = data.get("response")
                if isinstance(resp, dict):
                    token = str(resp.get("accessToken") or "")
            if not token:
                raise RemnawaveAuthError("В ответе логина нет accessToken")
            self._token = token
            return token
