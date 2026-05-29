# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Что это

Telegram-бот (Python, aiogram 3) для сервиса VPN-подписок. Бот **read-only по
отношению к подписке**: он даёт инструкции, открывает страницу оплаты как
Telegram Mini App и в личном кабинете показывает ссылку-подписку, подтягивая её
из панели **Remnawave по Telegram ID** пользователя. Бот **не** обрабатывает
оплату и **не** создаёт/продлевает пользователей в Remnawave.

## Команды

В системе **нет** `pip`/`venv`/системного Python-окружения — зависимости
управляются через **`uv`** (бинарник установлен в snap-путь VS Code,
`XDG_DATA_HOME`, обычно `~/snap/code/*/.local/bin/uv`). Виртуальное окружение
`.venv/` уже создано со всеми зависимостями.

```bash
# Запуск бота (окружение уже готово)
.venv/bin/python -m bot

# Переустановить/обновить зависимости (найти uv, если нет в PATH):
UV="$(find "$HOME" /home/goga/snap -maxdepth 7 -name uv -type f 2>/dev/null | head -1)"
"$UV" pip install -r requirements.txt   # ставит в активный ./.venv

# Быстрая проверка синтаксиса всех модулей
.venv/bin/python -m py_compile bot/*.py bot/handlers/*.py

# Проверка, что всё импортируется и собирается (BOT_TOKEN нужен для Settings)
BOT_TOKEN=x:y PYTHONPATH="$PWD" .venv/bin/python -c "import bot.__main__"
```

Формального test-suite в репозитории нет. Конфигурация читается из `.env`
(скопировать из `.env.example`); обязателен `BOT_TOKEN`.

## Архитектура

Поток: `/start` → главное меню (inline). Кнопка **«Оплатить»** — это `web_app`
на `PAYMENT_URL` (`https://aiyl-bank.ru/checkout`). Кнопка **«Личный кабинет»**
→ `handlers/account.py` берёт `callback.from_user.id` (нефальсифицируемый
Telegram ID) → `RemnawaveClient.get_users_by_telegram_id(...)` → `texts.account()`.

**Внедрение зависимостей (важно и неочевидно):** в `bot/__main__.py` объекты
кладутся в `dp["settings"]` и `dp["remnawave"]`, а aiogram прокидывает их в
обработчики **по имени параметра**. Новый хендлер, которому нужны эти объекты,
должен объявлять параметры ровно `settings: Settings` и/или
`remnawave: RemnawaveClient` — иначе они не придут.

**`bot/remnawave.py`** — тонкий async-клиент на `httpx`, повторяющий логику
Go-бэка сайта: авторизация статичным Bearer-токеном **или** логином/паролем
(`POST /api/auth/login`, с однократным релогином при 401), все ответы обёрнуты в
`{"response": ...}`. Функция `_extract_users` намеренно устойчива к разным
формам ответа `by-telegram-id` (список / `{response:[...]}` / `{response:{users:[]}}`
/ одиночный объект), потому что точная форма не зафиксирована. `_parse_iso`
обрезает наносекунды (их не принимает `datetime.fromisoformat`).

**`bot/config.py`** (`pydantic-settings`): `REMNAWAVE_BASE_URL` с хостом
`example.com` трактуется как «не задано»; `remnawave_enabled` требует URL +
(токен **или** логин/пароль). В `keyboards.py` кнопка оплаты использует `web_app`
только для HTTPS-URL, иначе откатывается на обычную `url`-кнопку (Telegram не
принимает WebApp на не-HTTPS).

Бот не падает, если Remnawave недоступен или не настроен — личный кабинет
показывает понятное сообщение.

## Граница с сайтом (критично)

Личный кабинет находит подписку только если сайт оплаты при создании
пользователя записывает `telegramId` в Remnawave. Текущий бэкенд сайта этого
**не делает** (создаёт юзера со случайным `username`). Точный контракт правок
сайта — в **`SITE_INTEGRATION.md`** (связанный репозиторий
`github.com/Goga211/vpn_web`, Go). При работе над ботом **не** добавляй создание/
продление юзеров; если ЛК отвечает «подписка не найдена» — первая гипотеза, что
сайт ещё не пишет `telegramId`, а не баг бота.

Подробности запуска и переменные `.env` — в `README.md`.

## Язык

Весь пользовательский текст, комментарии и коммуникация — на русском. Тексты
сообщений вынесены в `bot/texts.py` (HTML-разметка Telegram).
