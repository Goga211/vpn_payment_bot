# Контракт интеграции сайта (`vpn_web`) с ботом

Чтобы личный кабинет бота находил подписку по Telegram ID, бэкенд сайта при
создании пользователя в Remnawave должен **записывать `telegramId`**, а сам ID
брать из **проверенного** `initData` Telegram Mini App.

Сейчас сайт создаёт пользователя со случайным `username`, а телеграм пишет
только в локальный `data/checkouts.json`. В панель `telegramId` не попадает,
поэтому `GET /api/users/by-telegram-id/{id}` возвращает пусто.

Ниже — минимальный набор правок. Файлы указаны относительно корня `vpn_web`.

---

## 1. Фронтенд — сделать страницу Mini App

**`frontend/index.html`** — подключить SDK Telegram (до бандла):

```html
<script src="https://telegram.org/js/telegram-web-app.js"></script>
```

**`frontend/src/components/Checkout.tsx`** — при оформлении передавать
`initData` (сырую строку) на бэкенд. Telegram сам кладёт её в `window.Telegram`,
когда страница открыта как Web App из бота.

```ts
const tg = (window as any).Telegram?.WebApp
tg?.ready()
tg?.expand()

const result = await createCheckout({
  planId: selectedPlan.id,
  email: email.trim(),
  consent,
  initData: tg?.initData ?? '',   // ← НОВОЕ: сырая подписанная строка
})
```

> Поле ручного ввода `@username` больше не нужно для привязки — Telegram ID
> приходит из `initData`. Оставьте его максимум как необязательный контакт.

**`frontend/src/types.ts`** — добавить `initData?: string` в `CheckoutPayload`.

---

## 2. Бэкенд — принять и проверить `initData`

### 2.1 `internal/config/config.go`

Добавить токен бота (нужен для проверки подписи `initData`):

```go
TelegramBotToken string   // поле в struct Config
// ...в Load():
TelegramBotToken: getEnv("TELEGRAM_BOT_TOKEN", ""),
```

И в `.env`:

```env
TELEGRAM_BOT_TOKEN=   # тот же токен, что BOT_TOKEN у бота
```

### 2.2 Проверка `initData` (новый файл `internal/telegram/initdata.go`)

```go
package telegram

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ValidateInitData проверяет подпись Telegram WebApp initData и возвращает Telegram ID.
// Алгоритм: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
func ValidateInitData(initData, botToken string, maxAge time.Duration) (int64, error) {
	if initData == "" || botToken == "" {
		return 0, errors.New("empty initData or bot token")
	}
	values, err := url.ParseQuery(initData)
	if err != nil {
		return 0, err
	}
	hash := values.Get("hash")
	if hash == "" {
		return 0, errors.New("no hash in initData")
	}
	values.Del("hash")

	keys := make([]string, 0, len(values))
	for k := range values {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var sb strings.Builder
	for i, k := range keys {
		if i > 0 {
			sb.WriteByte('\n')
		}
		sb.WriteString(k + "=" + values.Get(k))
	}

	// secret = HMAC_SHA256(key="WebAppData", data=botToken)
	secret := hmacSHA256([]byte("WebAppData"), []byte(botToken))
	// expected = HMAC_SHA256(key=secret, data=dataCheckString)
	expected := hex.EncodeToString(hmacSHA256(secret, []byte(sb.String())))
	if !hmac.Equal([]byte(expected), []byte(hash)) {
		return 0, errors.New("bad initData signature")
	}

	// Защита от повторного использования (replay).
	if maxAge > 0 {
		if authDate, err := strconv.ParseInt(values.Get("auth_date"), 10, 64); err == nil {
			if time.Since(time.Unix(authDate, 0)) > maxAge {
				return 0, errors.New("initData expired")
			}
		}
	}

	var user struct {
		ID int64 `json:"id"`
	}
	if err := json.Unmarshal([]byte(values.Get("user")), &user); err != nil || user.ID == 0 {
		return 0, errors.New("no user id in initData")
	}
	return user.ID, nil
}

func hmacSHA256(key, data []byte) []byte {
	h := hmac.New(sha256.New, key)
	h.Write(data)
	return h.Sum(nil)
}
```

### 2.3 `internal/api/handlers.go`

В `checkoutRequest` добавить поле и проверять подпись. **Telegram ID берётся
только из проверенного `initData`, никогда из тела запроса напрямую** — иначе
любой подставит чужой ID и получит чужую подписку.

```go
type checkoutRequest struct {
	PlanID   string `json:"planId"`
	Email    string `json:"email"`
	Consent  bool   `json:"consent"`
	InitData string `json:"initData"` // ← НОВОЕ
}

// в handleCheckout, после базовой валидации:
telegramID, err := telegram.ValidateInitData(req.InitData, s.cfg.TelegramBotToken, 24*time.Hour)
if err != nil {
	writeError(w, http.StatusBadRequest, "bad_init_data",
		"Откройте оплату через бота в Telegram.")
	return
}

result, err := s.checkout.Start(provisionCtx, checkout.CreateInput{
	PlanID:     req.PlanID,
	Email:      req.Email,
	TelegramID: telegramID, // ← НОВОЕ
})
```

### 2.4 `internal/checkout/store.go` и `service.go`

Пробросить `TelegramID` по цепочке:

```go
// CreateInput и Checkout — добавить поле:
TelegramID int64 `json:"telegramId,omitempty"`

// в Service.Provision при формировании remnawave.CreateUserRequest:
user, err := s.remna.CreateUser(ctx, remnawave.CreateUserRequest{
	Username:   username,
	TelegramID: checkout.TelegramID, // ← НОВОЕ
	// ...остальные поля без изменений
})
```

### 2.5 `internal/remnawave/client.go`

Добавить поле в запрос создания пользователя:

```go
type CreateUserRequest struct {
	Username   string `json:"username"`
	TelegramID int64  `json:"telegramId,omitempty"` // ← НОВОЕ
	// ...остальные поля без изменений
}
```

### 2.6 Заголовки безопасности (`main.go`, функция `securityHeaders`) — ⚠️ обязательно

Текущий CSP блокирует Mini App — без этой правки **ничего не заработает**:

* `script-src 'self'` не даст загрузить `telegram-web-app.js` с `telegram.org`;
* `frame-ancestors 'none'` + `X-Frame-Options: DENY` не дадут открыть страницу
  в **веб-версии** Telegram (web.telegram.org встраивает Mini App в iframe;
  нативные клиенты iOS/Android/Desktop работают через WebView и не затронуты).

```go
w.Header().Set("Content-Security-Policy",
	"default-src 'self'; "+
		"script-src 'self' https://telegram.org; "+ // ← разрешить SDK Telegram
		"style-src 'self'; "+
		"img-src 'self' data:; "+
		"connect-src 'self'; "+
		"frame-ancestors https://web.telegram.org https://telegram.org; "+ // ← для web-Telegram
		"base-uri 'self'; form-action 'self'")
// X-Frame-Options для HTML не ставить: заголовок не умеет несколько источников
// и конфликтует с frame-ancestors. Управление встраиванием — через CSP.
```

> Эта функция в `main.go` оборачивает и статику, и `/api`, и именно она отдаёт
> заголовки для HTML-страницы `/checkout` — достаточно поправить её.
> Дублирующий `withSecurityHeaders` в `internal/api/handlers.go` влияет лишь на
> JSON-ответы `/api/*` (там скрипты/iframe не важны), синхронизировать по желанию.
>
> Если после включения «поедут» темы/вёрстка — добавьте `'unsafe-inline'` в
> `style-src` (Telegram прокидывает тему через CSS-переменные).

### 2.7 Продление вместо дублей (важно для корректного ЛК)

Сейчас каждый успешный checkout вызывает `CreateUser`. При повторной оплате тем
же пользователем в панели появятся **несколько** юзеров с одним `telegramId`, и
личный кабинет покажет их списком. Чтобы оплата продлевала доступ:

1. перед созданием найти юзера: `GET /api/users/by-telegram-id/{telegramID}`;
2. если активный есть — продлить через `PATCH /api/users` (обновить `expireAt` =
   бо́льшая из «текущий expireAt» / «сейчас» + срок плана) вместо создания;
3. если нет — создавать как сейчас, уже с `telegramId`.

Не блокирует запуск, но без этого со временем копятся дубли.

## Важно: следствия и что трогать НЕ нужно

* **`/checkout` уже открывается.** `main.go` отдаёт `index.html` на неизвестные
  пути (SPA-fallback), поэтому прямой заход на `/checkout` (куда ведёт кнопка
  бота) работает — отдельная правка роутинга не нужна.
* **`initData` есть только внутри Telegram.** После правок `/api/checkout`
  принимает заявку лишь с валидным `initData`. Если сайт ещё используется как
  публичный лендинг с оплатой из браузера — там `initData` пустой и привязки к
  Telegram не будет. Реши заранее: принимать оплату только через бота, либо
  оставить браузерный путь (но такие подписки бот по Telegram ID не найдёт).
* **Платные тарифы.** В `handlers.go` сейчас стоит блок `paid_plans_disabled`
  (разрешён только `trial`), а доступ выдаётся сразу по сабмиту формы (стаб без
  реальной оплаты). Привязку `telegramId` это не ломает, но «оплата на aiyl-bank»
  и снятие ограничения — отдельная задача платёжной интеграции, вне этого контракта.

---

## 3. Проверка

После внедрения:

```bash
# Пользователь оплатил через Mini App → в панели у него заполнен Telegram ID.
curl -s https://panel.your-domain.com/api/users/by-telegram-id/123456789 \
  -H "Authorization: Bearer $REMNAWAVE_TOKEN" | jq .
```

В ответе должен быть пользователь с непустым `subscriptionUrl`. После этого
личный кабинет бота начнёт показывать подписку без каких-либо изменений в боте.

---

## Чек-лист

- [ ] `telegram-web-app.js` подключён, фронт шлёт `initData`.
- [ ] **CSP/заголовки разрешают Telegram** (`script-src ... telegram.org`,
      `frame-ancestors ... web.telegram.org`, без `X-Frame-Options: DENY` на HTML).
- [ ] `TELEGRAM_BOT_TOKEN` задан в `.env` сайта (= токену бота).
- [ ] `initData` проверяется по подписи, ID берётся из неё.
- [ ] `telegramId` уходит в `POST /api/users` при создании пользователя.
- [ ] Повторная оплата продлевает доступ, а не плодит дубли (`PATCH`, опц.).
- [ ] `GET /api/users/by-telegram-id/{id}` возвращает пользователя.
