# QMenu Backend — гайд для фронтенда

Документ описывает **фактически реализованный API** и его соответствие
`WEB_BACKEND_PRODUCT_CONTRACT.md`. Всё, что здесь написано, покрыто сквозным
тестом (`tests/test_flow.py`) и доступно в Swagger: `http://127.0.0.1:8000/docs`.

Обновлено: 2026-07-02.

Обозначения:
- ✅ — как в контракте;
- ⚠️ — реализовано с отличием (все отличия собраны в разделе 2);
- поля запросов/ответов ниже — фактические имена, копируйте их как есть.

---

## 1. Общие правила (контракт, раздел 4)

**Base URL** ✅

```
/api/v1/auth/*      — авторизация CRM/KDS
/api/v1/crm/*       — CRM (нужен Bearer access token)
/api/v1/public/*    — гостевая зона (без CRM-токена)
/api/v1/kds/*       — кухня (Bearer access token)
```

**Response wrapper** ✅

```jsonc
// mutation / detail
{ "success": true, "message": "OK", "data": { ... } }

// списки
{ "data": [ ... ], "pagination": { "current_page": 1, "last_page": 5, "per_page": 20, "total": 95 } }
```

**Пагинация** ✅ — каждый list-эндпоинт принимает `limit` (default 20, max 200),
`offset`, `page`. Если передан `page`, `offset` вычисляется на сервере.

**Формат ошибок** ✅

```jsonc
{ "success": false, "message": "Запись не найдена", "code": "NOT_FOUND" }

// ошибки форм (422 или 400/409) — с field_errors по именам полей запроса:
{
  "success": false,
  "message": "Проверьте поля формы",
  "code": "VALIDATION_ERROR",
  "field_errors": { "title": ["Field required"], "file": ["Допустимы только изображения JPEG/PNG/WebP/GIF"] }
}
```

Коды: `NOT_FOUND` (404), `FORBIDDEN` (403), `INVALID_CREDENTIALS` (401),
`VALIDATION_ERROR` (400/422), `CONFLICT` (409), а также специальные:
`CATEGORY_HAS_ITEMS`, `TABLE_NUMBER_TAKEN`, `TABLE_HAS_ACTIVE_SESSION`,
`LOGIN_TAKEN`, `ACTION_FAILED`, `INTERNAL_ERROR` (500, без деталей).

**Даты** ✅ — ISO 8601 (`"2026-07-02T10:00:00+00:00"`).

**Деньги** ⚠️ — см. раздел 2.1.

**Картинки** ⚠️ — см. раздел 2.2.

---

## 2. Отличия от вашего контракта — читать обязательно

### 2.1 Деньги: `price_minor` в тыйынах, не `price` в сомах

Все цены — **целые числа в тыйынах** (1 сом = 100 тыйын):

| Контракт | Фактически | Пример |
| --- | --- | --- |
| `price: 520` (сомы) | `price_minor: 52000` (тыйыны) | 520 сом |
| `total` | `total_minor` | |
| `price_snapshot` (в OrderItem) | `price_minor` | |

На UI: `price_minor / 100`. Это жёсткий инвариант backend (снапшоты цен,
никаких float) — просьба заложить хелпер форматирования один раз.

### 2.2 Картинки: отдельный upload-эндпоинт, CRUD остаётся JSON

Create/Update компаний/филиалов/категорий/блюд — **обычный JSON**,
а не `multipart/form-data`. Файл загружается отдельно:

```
POST /api/v1/crm/uploads
Content-Type: multipart/form-data
поле: file (File)

→ { "success": true, "data": { "image_url": "/uploads/abc123.png" } }
```

Флоу формы с картинкой:
1. пользователь выбрал файл → фронт сразу шлёт его в `POST /crm/uploads`;
2. полученный `image_url` подставляется в JSON-поле `logo_url` / `cover_url` /
   `image_url` при create/PATCH;
3. при PATCH без этого поля старая картинка сохраняется (contract-совместимо).

Правила контракта соблюдены: фронт не придумывает URL сам, backend валидирует
тип (JPEG/PNG/WebP/GIF) и размер (5 МБ) и возвращает готовый URL.
Отдаются файлы по `GET /uploads/<имя>` (относительный путь от корня хоста).

### 2.3 Гость: `X-Device-Token`, а не `X-Participant-Token`

| Контракт | Фактически |
| --- | --- |
| `X-Participant-Token` header | **`X-Device-Token`** header |
| `participant_token` в ответе scan | `device_token` |
| `POST /public/tables/scan` | `POST /public/sessions/scan` |
| `participant_name` в scan body | `display_name` |

Токен выдаётся на первом scan (если не прислать свой), хранится у гостя
(localStorage) и шлётся в заголовке `X-Device-Token` во все session-запросы.
В теле создания заказа поле `device_token` **тоже обязательно** (должно
совпадать с заголовком).

### 2.4 Статусы заказа: без отдельного `moderation_status`

Один enum `status`: `pending → approved → cooking → ready → served`,
плюс `rejected` и `cancelled`. Отличия от контракта:

| Контракт | Фактически |
| --- | --- |
| `pending_moderation` | `pending` |
| `moderation_status: pending/approved/rejected` | вычисляйте из `status` |
| `moderated_at` | нет (есть `updated_at`) |
| `moderated_by` | ✅ есть (id сотрудника или null, если модерировал владелец/супер-админ) |

Причина отмены/отклонения — в одном поле `reject_reason`.

### 2.5 Имена полей в заказах

| Контракт | Фактически | Где |
| --- | --- | --- |
| `items[].quantity` | `qty` | тело создания заказа, CRM/guest ответы |
| `items[].title_snapshot` | `title` | CRM/guest ответы заказа |
| `items[].quantity` | `quantity` ✅ | только KDS DTO |
| `comment` | ✅ `comment` | везде |

### 2.6 Прочее

- `type_ids` в **CRM-формах** называется `type_codes` (массив строк JSON:
  `["coffee","restaurant"]`, не csv-строка). В **публичных ответах** поле
  называется `type_ids` по контракту.
- Хост подтверждает участника: `POST /public/sessions/{id}/decide` с телом
  `{"participant_id": 5, "approve": true}` (не per-participant путь).
  CRM-вариант — контрактный: `POST /crm/sessions/{id}/participants/{pid}/decide`
  с `{"decision": "approved" | "rejected"}`.
- `/crm/branches/my` из контракта живёт на `GET /crm/me/branches`
  (для кухни — `GET /kds/branches/my`).
- Логин-ответ содержит только токены; профиль/роль берите из `GET /auth/me`
  (это соответствует frontend behavior контракта).
- Справочник restaurant-types создаётся seed-данными; CRM CRUD для него нет
  (контракт это допускает). 6 типов: `coffee, chaikhana, restaurant, fastfood,
  pizza, sushi`.
- `GET /api/v1/crm/companies/` (список/создание) — со слэшем на конце
  (иначе 307 redirect).

### 2.7 Фильтры и сортировки: что есть, а чего НЕТ

Контракт (раздел 4, Common filters) описывает широкий набор фильтров.
Реализовано **подмножество** — закладывайте это в UI сейчас, остальное
появится этапом 3.

**НЕ реализовано ни на одном списке** (сейчас):

| Параметр из контракта | Статус |
| --- | --- |
| `sort_by`, `sort_order` | ❌ нет; сортировка фиксированная (см. таблицу ниже) — контролы сортировки в таблицах пока не делать или делать client-side в рамках страницы |
| `created_at_from`, `created_at_to` | ❌ нет — фильтры по датам не делать |
| `updated_at_from`, `updated_at_to` | ❌ нет |
| `statuses=pending,approved` (мульти-статус csv) | ❌ нет — только одиночный `status=` |
| `search` на CRM-списках компаний/филиалов/категорий/блюд/столов | ❌ нет (есть только там, где указано ниже) |

**Точная карта по каждому list-эндпоинту** (пагинация `limit/offset/page`
есть везде; здесь — только фильтры и порядок выдачи):

| Эндпоинт | Фильтры | Порядок выдачи |
| --- | --- | --- |
| `GET /crm/companies/` | — (только пагинация) | по `id` |
| `GET /crm/companies/{id}/branches` | — | по `id` |
| `GET /crm/branches/{id}/categories` | — | `sort_order`, затем `id` |
| `GET /crm/branches/{id}/items` | — | `sort_order`, затем `id` |
| `GET /crm/branches/{id}/tables` | — | по `id` |
| `GET /crm/branches/{id}/employees` | — | по `id` |
| `GET /crm/companies/{id}/employees` | `branch_id` | по `id` |
| `GET /crm/users` | `search` (login+ФИО), `is_active` | по `id` |
| `GET /crm/users/search` | `query` (обязателен, min 1 символ) | по `id`, max 20 |
| `GET /crm/branches/{id}/orders` | `status` (один), `table_id` | новые сверху (`-created_at`) |
| `GET /crm/branches/{id}/moderation` | — (это и есть фильтр `status=pending`) | новые сверху |
| `GET /crm/branches/{id}/sessions` | `status` (`open`/`closed`), `table_id` | новые сверху (`-opened_at`) |
| `GET /public/restaurant-types` | — | `sort_order` |
| `GET /public/places` | `search` (название+описание), `type_ids` (csv кодов), `city` | по `id` |
| `GET /public/places/{slug}/branches` | `city` | по `id` |
| `GET /public/branches/{slug}/menu/search` | `search` (название+описание), `category_id`, `is_available` | `sort_order`, затем `id` |
| `GET /public/sessions/{id}/orders` | — | новые сверху |
| `GET /kds/branches/{id}/orders` | — (доска сама фильтрует approved/cooking/ready) | новые сверху |

Примечания:
- булевы фильтры передаются строкой: `is_active=true` / `is_available=false`;
- `type_ids` — единственный csv-параметр: `?type_ids=coffee,restaurant`;
- порядок категорий/блюд управляется не сортировкой списка, а полем
  `sort_order` + эндпоинтами `POST .../categories/reorder` и
  `POST .../items/reorder` — drag-and-drop в CRM реализуйте через них;
- `GET /kds/branches/{id}/orders` не принимает `status`/`cooking_zone`
  из контракта — доска всегда отдаёт полный рабочий набор кухни.

---

## 3. Auth (`/api/v1/auth`) ✅

| Метод | Путь | Тело / заголовок | Ответ `data` |
| --- | --- | --- | --- |
| POST | `/auth/login` | `{"login": "admin", "password": "admin"}` | `{access_token, refresh_token}` |
| GET | `/auth/me` | `Authorization: Bearer <access>` | см. ниже |
| POST | `/auth/refresh` | `Authorization: Bearer <refresh>` | новая пара токенов |
| POST | `/auth/logout` | `Authorization: Bearer <refresh>` | `null` |

`GET /auth/me` — контрактный ответ:

```json
{
  "id": 1, "login": "owner", "full_name": "Owner User",
  "role": "owner", "roles": ["owner"],
  "company_ids": [1], "branch_ids": [11, 12],
  "permissions": ["companies.read", "menu.manage", "orders.manage", "..."]
}
```

Роли: `super_admin`, `owner`, `branch_admin`, `waiter` (⚠️ дополнительная роль,
нет в контракте — официант: только заказы/модерация), `kitchen`.

Refresh — **ротация**: после `/auth/refresh` старый refresh-токен мёртв,
сохраняйте новую пару. Access-токен живёт 30 минут; по 401 → refresh → повтор
запроса → при неудаче refresh → на login (ровно как в контракте).

---

## 4. CRM (`/api/v1/crm`, всё под Bearer access token)

### 4.1 Компании ✅

| Метод | Путь | Примечание |
| --- | --- | --- |
| GET | `/crm/companies/` | пагинация; super_admin — все, owner — свои |
| POST | `/crm/companies/` | JSON, см. поля ниже |
| GET | `/crm/companies/{id}` | |
| PATCH | `/crm/companies/{id}` | частичное обновление |
| DELETE | `/crm/companies/{id}` | 204 |

Поля create/PATCH: `title`, `description`, `short_description`,
`type_codes: string[]`, `logo_url`, `cover_url`,
`status: draft|active|archived`, `is_published: bool`, `is_active: bool`.
`slug` генерируется сервером из title (транслитерация), приходит в ответе.

### 4.2 Филиалы ✅

| Метод | Путь |
| --- | --- |
| GET/POST | `/crm/companies/{company_id}/branches` |
| PATCH/DELETE | `/crm/companies/{company_id}/branches/{branch_id}` |
| GET | `/crm/me/branches` — мои филиалы (после логина) |

Поля: `title`, `address`, `city`, `latitude?`, `longitude?`, `phone?`,
`cover_url?`, `working_hours?` (строка для UI), `schedule` (массив объектов
`{day_of_week: 1..7, opens_at: "09:00", closes_at: "22:00", is_closed: false}`
— JSON-массив, не строка), `moderation_mode: strict|auto`, `status`,
`is_published`, `is_active`. `slug` — серверный. `is_open` вычисляется
backend'ом из `schedule` (в публичных ответах).

### 4.3 Настройки филиала ✅

`GET|PATCH /crm/branches/{branch_id}/settings`:

```json
{
  "branch_id": 1,
  "moderation_mode": "strict",
  "allow_guest_join_without_host": false,
  "allow_order_without_approval": false,
  "is_active": true,
  "is_published": true
}
```

Настройки реально работают: `auto` — заказ сразу уходит на кухню (минуя
модерацию); `allow_guest_join_without_host` — новый гость сразу `approved`;
`allow_order_without_approval` — pending-гость может заказывать.

### 4.4 Категории меню ✅

| Метод | Путь |
| --- | --- |
| GET/POST | `/crm/branches/{branch_id}/categories` |
| PATCH/DELETE | `/crm/branches/{branch_id}/categories/{category_id}` |
| POST | `/crm/branches/{branch_id}/categories/reorder` — `{"category_ids": [3,1,2]}` |

Поля: `title`, `description?`, `image_url?`, `sort_order`, `is_active`,
`is_published`. Удаление категории с блюдами → 409 `CATEGORY_HAS_ITEMS`.

### 4.5 Блюда ✅

| Метод | Путь |
| --- | --- |
| GET/POST | `/crm/branches/{branch_id}/items` |
| PATCH/DELETE | `/crm/branches/{branch_id}/items/{item_id}` |
| POST | `/crm/branches/{branch_id}/items/{item_id}/availability` — `{"is_available": false, "status": "stop_list"}` |
| POST | `/crm/branches/{branch_id}/items/reorder` — `{"category_id": 1, "item_ids": [102,101]}` |
| POST | `/crm/branches/{branch_id}/menu/copy-from` — см. ниже |

Поля блюда: `category_id`, `title`, `description?`, `price_minor` (тыйыны!),
`image_url?`, `weight?`, `weight_unit?: g|ml|pcs`, `sort_order`,
`status: active|hidden|stop_list`, `is_available`, `is_published`,
`cooking_zone` (default `kitchen`).

Copy-from (owner/super_admin):
`{"source_branch_id": 11, "copy_categories": true, "copy_items": true, "replace_existing": false}`
→ `{"copied_categories": 2, "copied_items": 10, "replaced_existing": false}`.

### 4.6 Столы ✅

| Метод | Путь |
| --- | --- |
| GET/POST | `/crm/branches/{branch_id}/tables` |
| GET/PATCH/DELETE | `/crm/branches/{branch_id}/tables/{table_id}` |
| POST | `/crm/branches/{branch_id}/tables/bulk` |
| POST | `/crm/branches/{branch_id}/tables/{table_id}/regenerate-qr` |
| GET | `/crm/branches/{branch_id}/tables/{table_id}/qr` |

Стол: `{id, branch_id, title, number, zone, seats, qr_token, is_active, public_url}` —
`public_url` готов для QR (контрактное правило соблюдено).
Bulk: `{"zone": "Главный зал", "prefix": "A", "from": 1, "to": 10, "seats": 4}`
→ массив столов `A-1..A-10` (номер = `prefix-номер`; конфликт → 409
`TABLE_NUMBER_TAKEN`). Удаление стола с активной сессией → 409
`TABLE_HAS_ACTIVE_SESSION`. `regenerate-qr` → `{qr_token, public_url}` —
старая ссылка сразу перестаёт работать.

### 4.7 Пользователи и сотрудники ✅

| Метод | Путь | Примечание |
| --- | --- | --- |
| GET | `/crm/users` | фильтры: `search`, `is_active` |
| POST | `/crm/users` | `{login, password, full_name, phone?, is_active}`; дубликат → 409 `LOGIN_TAKEN` + field_errors |
| GET/PATCH | `/crm/users/{user_id}` | PATCH: `full_name?, phone?, is_active?` |
| POST | `/crm/users/{user_id}/reset-password` | `{"password": "..."}`; отзывает все refresh-токены |
| GET | `/crm/users/search?query=иван` | searchable select |
| GET/POST | `/crm/branches/{branch_id}/employees` | POST: `{"user_id": 15, "role_code": "waiter"}` |
| PATCH | `/crm/branches/{branch_id}/employees/{employee_id}` | `{"role_code"?: "...", "status"?: "active"\|"blocked"}` — blocked теряет доступ сразу |
| DELETE | `/crm/branches/{branch_id}/employees/{employee_id}` | 204 |
| GET | `/crm/employees/{employee_id}` | деталка назначения |
| GET/POST | `/crm/companies/{company_id}/employees` | роли уровня компании; POST: `{"user_id": 12, "role": "owner"}` — owner назначает только super_admin |
| DELETE | `/crm/companies/{company_id}/employees/{employee_id}` | 204 |

⚠️ Поле роли: в branch employees — `role_code`, в company employees — `role`
(как в контракте 8.11). Доступ super_admin: все пользователи; owner — только
сотрудники своих компаний.

### 4.8 Заказы и модерация ✅

| Метод | Путь | Примечание |
| --- | --- | --- |
| GET | `/crm/branches/{branch_id}/orders` | фильтры: `status`, `table_id` |
| GET | `/crm/branches/{branch_id}/moderation` | очередь `pending` |
| GET | `/crm/orders/{order_id}` | плоская деталка |
| POST | `/crm/branches/{branch_id}/orders/{order_id}/approve` | → на кухню |
| POST | `.../reject` | `{"reason": "Позиция недоступна"}` |
| POST | `.../served` | выдан |
| POST | `.../cancel` | `{"reason"?: "..."}`; нельзя после served |

Заказ (CRM/guest ответ):

```json
{
  "id": 1, "branch_id": 1, "session_id": 1,
  "table": {"id": 1, "number": "A1", "zone": "Зал"},
  "participant": {"id": 1, "name": "Гость"},
  "participant_id": 1, "participant_name": "Гость",
  "status": "pending", "total_minor": 20000,
  "comment": null, "reject_reason": null, "moderated_by": null,
  "items": [
    {"id": 1, "menu_item_id": 1, "title": "Чай", "price_minor": 10000, "qty": 2, "comment": null}
  ],
  "created_at": "...", "updated_at": "..."
}
```

### 4.9 Сессии столов ✅

| Метод | Путь | Примечание |
| --- | --- | --- |
| GET | `/crm/branches/{branch_id}/sessions` | фильтры: `status: open|closed`, `table_id` |
| GET | `/crm/sessions/{session_id}` | + `participants[]`, `orders[]` |
| POST | `/crm/sessions/{session_id}/close` | закрыть админом |
| GET | `/crm/sessions/{session_id}/participants` | |
| POST | `/crm/sessions/{session_id}/participants/{pid}/decide` | `{"decision": "approved"|"rejected"}` |

### 4.10 Сводка филиала ✅

`GET /crm/branches/{branch_id}/summary`:

```json
{
  "active_sessions_count": 2, "pending_orders_count": 1,
  "cooking_orders_count": 0, "ready_orders_count": 0,
  "unavailable_items_count": 0, "tables_count": 5
}
```

---

## 5. Guest Public (`/api/v1/public`, без авторизации)

### 5.1 Каталог (до QR) ✅

| Метод | Путь | Фильтры |
| --- | --- | --- |
| GET | `/public/restaurant-types` | — |
| GET | `/public/places` | `search`, `type_ids` (csv: `coffee,restaurant`), `city`, пагинация |
| GET | `/public/places/{place_slug}` | деталка + branches[] |
| GET | `/public/places/{place_slug}/branches` | `city`, пагинация |
| GET | `/public/branches/{branch_slug}` | деталка филиала + place |
| GET | `/public/places/{place_slug}/branches/{branch_slug}/menu` | preview-меню |
| GET | `/public/branches/{branch_slug}/menu` | короткий вариант |
| GET | `/public/branches/{branch_slug}/menu/search` | `search`, `category_id`, `is_available`, пагинация |
| GET | `/public/branches/{branch_slug}/menu/items/{item_id}` | деталка блюда (для модалки) |
| GET | `/public/tables/{qr_token}` | превью стола до входа в сессию |

Карточка заведения: `{id, slug, title, short_description, type_ids, type_title,
logo_url, cover_url, branches_count}` — как в контракте. Отдаются только
`is_active=true && is_published=true`. Блюдо в preview:
`{id, title, description, image_url, price_minor, weight, weight_unit, is_available}`.
`is_available=false` — блюдо видно, но недоступно (стоп-лист).

### 5.2 Сессия стола (после QR) ⚠️ header `X-Device-Token`

| Метод | Путь | Тело / заголовок |
| --- | --- | --- |
| POST | `/public/sessions/scan` | `{"qr_token": "...", "device_token"?: "...", "display_name"?: "Гость"}` |
| GET | `/public/sessions/{id}/state` | header `X-Device-Token` |
| GET | `/public/sessions/{id}/participants` | — |
| POST | `/public/sessions/{id}/decide` | host; `{"participant_id": 5, "approve": true}` + header |
| PATCH | `/public/sessions/{id}/participants/me` | `{"name": "Даурен"}` + header |
| POST | `/public/sessions/{id}/participants/me/leave` | header; хосту запрещено (409) |
| POST | `/public/sessions/{id}/close` | host + header |

Ответ scan:

```json
{
  "device_token": "СОХРАНИТЬ-НА-КЛИЕНТЕ",
  "session": {"id": 1, "status": "open"},
  "participant": {"id": 1, "display_name": "Гость", "status": "host"},
  "can_order": true,
  "is_host": true
}
```

Первый гость — `host`; следующие — `pending` (ждут решения хоста) либо сразу
`approved`, если в настройках филиала `allow_guest_join_without_host=true`.
Статусы участника: `host | pending | approved | rejected | left`.
Поллинг `state` — гость узнаёт, подтвердили ли его (`can_order`).

### 5.3 Заказы гостя ✅ (+ header и `device_token` в теле)

| Метод | Путь | Тело |
| --- | --- | --- |
| POST | `/public/sessions/{id}/orders` | см. ниже |
| GET | `/public/sessions/{id}/orders` | пагинация |
| GET | `/public/sessions/{id}/orders/{order_id}` | header |
| POST | `/public/sessions/{id}/orders/{order_id}/cancel` | `{"reason"?: "Передумали"}` |

Создание заказа (корзина живёт на фронте — контрактное правило 3):

```json
{
  "device_token": "тот же, что в заголовке",
  "comment": "Без лука",
  "items": [
    {"menu_item_id": 401, "qty": 2, "comment": "Острое отдельно"}
  ]
}
```

Backend сам: проверяет сессию/права участника/принадлежность блюд филиалу/
доступность, снапшотит название+цену, считает `total_minor`. При
`moderation_mode=auto` заказ возвращается сразу со `status="approved"`.
Отмена гостем — только свои заказы (host — любые) и только до кухни
(`pending`/`approved`), иначе 409.

---

## 6. KDS (`/api/v1/kds`, Bearer, роль kitchen) ✅

| Метод | Путь |
| --- | --- |
| GET | `/kds/branches/my` |
| GET | `/kds/branches/{branch_id}/orders` |
| GET | `/kds/branches/{branch_id}/orders/{order_id}` |
| POST | `/kds/branches/{branch_id}/orders/{order_id}/cooking` |
| POST | `/kds/branches/{branch_id}/orders/{order_id}/ready` |
| POST | `/kds/branches/{branch_id}/orders/{order_id}/served` |

Доска показывает только `approved | cooking | ready`. KdsOrder DTO
(без CRM-полей, как требует контракт):

```json
{
  "id": 1, "table_title": "A1", "table_zone": "Зал",
  "status": "approved", "comment": null, "created_at": "...",
  "items": [
    {"id": 1, "title_snapshot": "Чай", "quantity": 2, "comment": null, "status": "approved"}
  ]
}
```

⚠️ Статус позиции = статусу заказа (item-level статусы — следующий этап,
контракт это допускает). Переходы статусов защищены: недопустимый → 409.

---

## 7. Быстрый старт для проверки

```bash
# dev-сервер (создаст SQLite-схему и сиды: роли, типы заведений, admin/admin)
uvicorn main:app --reload    # Swagger: http://127.0.0.1:8000/docs

# супер-админ: login=admin, password=admin
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin"}'
```

CORS открыт для `http://localhost:3000` и `http://127.0.0.1:3000`.

Полный happy-path (login → CRUD → QR-скан → заказ → модерация → KDS →
отмены → настройки) можно посмотреть как «живую документацию» в
`tests/test_flow.py` — там реальные тела запросов на каждый эндпоинт.
