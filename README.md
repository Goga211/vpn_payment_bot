# VPN Payment Bot

Telegram-бот для сервиса подписок. Бот **не обрабатывает оплату** — он даёт
инструкции, открывает страницу оплаты как Telegram **Mini App** и показывает
личный кабинет с ссылкой-подпиской, которая подтягивается из панели
**Remnawave** по Telegram ID пользователя.

```
/start
 ├─ 💳 Оплатить            → Mini App: https://aiyl-bank.ru/checkout
 ├─ 👤 Личный кабинет      → Remnawave GET /api/users/by-telegram-id/{id}
 ├─ 📖 Как оплатить        → инструкция
 └─ 🔌 Как подключить      → настройка VPN-клиента
```

> ⚠️ **Важно.** Личный кабинет находит подписку по Telegram ID. Чтобы это
> работало, сайт оплаты должен при создании пользователя в Remnawave
> записывать `telegramId`. Сейчас бэкенд сайта этого **не делает** — нужные
> правки описаны в [`SITE_INTEGRATION.md`](./SITE_INTEGRATION.md). До их
> внедрения личный кабинет будет отвечать «подписка не найдена».

## Стек

- Python 3.11+
- [aiogram 3](https://docs.aiogram.dev/) — Telegram Bot API
- [httpx](https://www.python-httpx.org/) — async-клиент к Remnawave
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — конфигурация

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# отредактируйте .env
```

## Конфигурация (`.env`)

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | Токен бота из [@BotFather](https://t.me/BotFather) (обязательно) |
| `REMNAWAVE_BASE_URL` | Origin панели, **без** `/api` в конце |
| `REMNAWAVE_TOKEN` | Bearer-токен панели (предпочтительно) |
| `REMNAWAVE_USERNAME` / `REMNAWAVE_PASSWORD` | Альтернатива токену — логин/пароль |
| `REMNAWAVE_TIMEOUT` | Таймаут запросов к панели, сек (по умолчанию 12) |
| `PAYMENT_URL` | URL страницы оплаты для Mini App (обязательно HTTPS) |
| `SUPPORT_URL` | Ссылка на поддержку (необязательно) |
| `BRAND_NAME` | Название сервиса в приветствии |

Авторизация в Remnawave — **либо** `REMNAWAVE_TOKEN`, **либо** пара
`REMNAWAVE_USERNAME` + `REMNAWAVE_PASSWORD`. Для бота достаточно прав на чтение
пользователей.

## Запуск

```bash
python -m bot
```

## Настройка в BotFather (рекомендуется)

- **Menu Button** → можно повесить ту же страницу оплаты как Web App
  (`/setmenubutton` → URL = `PAYMENT_URL`).
- Команды: `/start` — главное меню.

## Структура

```
bot/
├── __main__.py        # точка входа, polling, DI
├── config.py          # .env → Settings (pydantic-settings)
├── remnawave.py       # async-клиент панели + модель пользователя
├── texts.py           # тексты сообщений (RU, HTML)
├── keyboards.py       # inline-клавиатуры (web_app-кнопка оплаты)
├── utils.py           # safe_edit для редактирования сообщений
└── handlers/
    ├── start.py       # /start, главное меню
    ├── account.py     # личный кабинет (Remnawave по Telegram ID)
    └── help.py        # инструкции
```

## Как это работает

1. `callback.from_user.id` — это Telegram ID (подделать нельзя, Telegram
   подписывает апдейты).
2. Бот делает `GET /api/users/by-telegram-id/{id}` к Remnawave.
3. Из ответа берётся `subscriptionUrl`, `expireAt`, `status` и показывается
   в личном кабинете.

Если панель недоступна или не настроена — бот не падает, а показывает
понятное сообщение и кнопку поддержки.
