# QMenu Backend — статус реализации контракта

Документ фиксирует, что сделано по `WEB_BACKEND_PRODUCT_CONTRACT.md` (этапы 1–2),
какие осознанные отклонения от контракта есть, и что запланировано на этап 3.

Для фронтенд-разработчика есть отдельный гайд по фактическому API со всеми
телами запросов и таблицей отличий от контракта: **`API_FOR_FRONTEND.md`**.

Обновлено: 2026-07-02.

---

## Этап 1 — фундамент (выполнен)

**Роли и доступ**
- Роли по контракту: `owner`, `branch_admin`, `waiter`, `kitchen`
  (`app/common/roles.py`). Старые `admin/manager/senior_waiter` удалены.
- `super_admin` — флаг `User.is_superadmin` (не запись Employee): платформенная
  роль без привязки к компании/филиалу. Все guard'ы (`require_manage`,
  `require_staff_action`, `require_branch_owner`, `check_branch_access`)
  пропускают его первым.
- `waiter` добавлен по требованию: модерирует заказы (approve/reject/served/
  cancel, очередь модерации), заказ закрепляется за ним через
  `Order.moderated_by`; меню/столы/сотрудники ему недоступны.

**Auth (`/api/v1/auth`)**
- `POST /login` — JSON `{login, password}` → `{access_token, refresh_token}`.
- `GET /me` — `role/roles/company_ids/branch_ids/permissions` (роль вычисляется:
  `super_admin > owner > branch_admin > waiter > kitchen`; permissions —
  статическая карта `PERMISSIONS_BY_ROLE`).
- `POST /refresh` — ротация: старый refresh отзывается, выдаётся новая пара.
  Refresh-токены хранятся в таблице `refresh_token` хэшированными (sha256).
- `POST /logout` — отзыв refresh-токена.
- Access-токен — JWT с TTL (30 мин по умолчанию, `ACCESS_TOKEN_TTL_MINUTES`).

**Единый формат ответов и ошибок**
- Mutation/detail: `{"success": true, "message": "...", "data": {...}}`.
- Списки: `{"data": [...], "pagination": {current_page, last_page, per_page, total}}`.
- Ошибки: `{"success": false, "message": "...", "code": "..."}`;
  ошибки валидации — с `field_errors` по полям (`app/common/errors.py`,
  handlers в `main.py`). Коды: `NOT_FOUND`, `FORBIDDEN`, `INVALID_CREDENTIALS`,
  `VALIDATION_ERROR`, `CONFLICT`, `CATEGORY_HAS_ITEMS`, `TABLE_NUMBER_TAKEN`,
  `TABLE_HAS_ACTIVE_SESSION`, `LOGIN_TAKEN`, `INTERNAL_ERROR`.
- Пагинация `limit/offset/page` (`app/common/pagination.py`) на всех списках.

**Namespace** `/api/v1/{auth, crm, public, kds}` — собран в `app/router.py`.

## Этап 2A — модель данных (выполнен)

- `RestaurantType` (справочник типов заведений) + идемпотентный seed 6 типов
  (`app/common/seed.py`): coffee, chaikhana, restaurant, fastfood, pizza, sushi.
- `Company`: + `slug` (уникальный, транслитерация кириллицы —
  `app/common/slug.py`), `description`, `short_description`, `type_codes`
  (JSON-список кодов), `logo_url`, `cover_url`, `status` (draft/active/archived),
  `is_published`, `updated_at`.
- `Branch`: + `slug`, `city`, `latitude/longitude`, `phone`, `cover_url`,
  `working_hours`, `schedule` (JSON: day_of_week/opens_at/closes_at/is_closed),
  `moderation_mode` теперь `strict|auto`, `allow_guest_join_without_host`,
  `allow_order_without_approval`, `status`, `is_published`.
- `MenuCategory`: + `slug`, `description`, `image_url`, `is_published`, даты.
- `MenuItem`: + `image_url` (вместо photo_url), `weight`, `weight_unit` (g/ml/pcs),
  `status` (active/hidden/stop_list), `is_available`, `is_published`,
  `cooking_zone`. Старый `is_in_stoplist` — вычисляемое свойство
  (`status == stop_list or not is_available`) для совместимости логики заказов.
- `Table`: + `title`, `seats`, `updated_at`.
- `Employee`: + `company` (FK, обязательный), `branch` стал nullable
  (роль уровня компании = branch=None), `status` (active/blocked).
- `SessionParticipant`: + статус `left`.
- `PATCH /crm/companies/{id}` (обновление компании) добавлен.

## Этап 2B — картинки и публичный каталог (выполнен)

**Загрузка картинок**
- `POST /crm/uploads` (multipart, поле `file`) → `{"image_url": "..."}`.
  Валидация типа (JPEG/PNG/WebP/GIF) и размера (5 МБ, `MAX_UPLOAD_BYTES`);
  ошибки — `VALIDATION_ERROR` с `field_errors.file`.
- Файлы в `uploads/`, раздача через `GET /uploads/...` (StaticFiles);
  `MEDIA_BASE_URL` для CDN на проде.
- Схема работы: фронт грузит файл, получает URL, шлёт его в `logo_url/cover_url/
  image_url` обычного JSON-тела create/update (см. «Отклонения» ниже).

**Публичный Guest-каталог (`/api/v1/public`, без авторизации)**
- `GET /restaurant-types` — активные типы.
- `GET /places` — опубликованные компании (search, type_ids csv, city,
  пагинация), карточка: slug/title/short_description/type_title/logo/cover/
  branches_count.
- `GET /places/{place_slug}` — деталка + филиалы.
- `GET /places/{place_slug}/branches` — филиалы отдельно (city, пагинация).
- `GET /places/{place_slug}/branches/{branch_slug}/menu` и
  `GET /branches/{branch_slug}/menu` — preview-меню (только опубликованное).
- `GET /branches/{branch_slug}` — деталка филиала (+ place summary,
  `is_open` вычисляется по `schedule` на текущее время).
- `GET /branches/{branch_slug}/menu/search` — поиск блюд (search, category_id,
  is_available, пагинация).
- `GET /branches/{branch_slug}/menu/items/{item_id}` — деталка блюда.
- `GET /tables/{qr_token}` — превью стола до скана (стол + филиал + заведение).

## Этап 2C — CRM-расширения и KDS (выполнен)

**Меню**
- `POST .../items/{id}/availability` — быстрый стоп-лист/доступность.
- `POST .../categories/reorder`, `POST .../items/reorder` — порядок по массиву id
  (с проверкой принадлежности филиалу/категории).
- `POST .../menu/copy-from` — копирование категорий/блюд между филиалами
  (owner обоих филиалов или super_admin; `replace_existing` очищает целевое меню;
  картинки переиспользуются по URL).
- Удаление непустой категории → 409 `CATEGORY_HAS_ITEMS`.

**Столы**
- `POST .../tables/bulk` — серия столов (`prefix`, `from`, `to`, до 100 шт.),
  каждому свой QR; конфликт номеров → 409 `TABLE_NUMBER_TAKEN`.
- `POST .../tables/{id}/regenerate-qr` — новый qr_token (старая ссылка умирает).
- `GET .../tables/{id}/qr` — данные для печати (`table_title`, `public_url`).
- Удаление стола с открытой сессией → 409 `TABLE_HAS_ACTIVE_SESSION`.

**Настройки филиала**
- `GET/PATCH /crm/branches/{id}/settings`: `moderation_mode`,
  `allow_guest_join_without_host`, `allow_order_without_approval`,
  `is_active`, `is_published`. Настройки реально влияют на flow:
  - `moderation_mode=auto` → заказ минует модерацию (сразу `approved` → KDS);
  - `allow_guest_join_without_host=true` → новый гость сразу `approved`;
  - `allow_order_without_approval=true` → pending-гость может заказывать.

**Пользователи и сотрудники**
- `/crm/users`: GET (search/is_active/пагинация), POST (создание с временным
  паролем; дубликат логина → 409 + field_errors), GET/{id}, PATCH/{id},
  POST/{id}/reset-password (отзывает все refresh-токены пользователя).
  Доступ: super_admin — все; owner — сотрудники своих компаний.
- `/crm/users/search` — searchable select по логину/имени.
- Branch employees: + `PATCH .../employees/{id}` (смена роли, block/unblock —
  blocked теряет доступ немедленно), `GET /crm/employees/{id}` — деталка.
- Company employees: `GET/POST/DELETE /crm/companies/{id}/employees` — роли
  уровня компании (branch=None); назначить `owner` может только super_admin.

**Заказы (CRM)**
- `GET /crm/branches/{id}/orders` — история с фильтрами (status, table_id).
- `GET /crm/orders/{id}` — плоская деталка (branch выводится из заказа,
  доступ через `check_branch_access`).
- `POST .../orders/{id}/cancel` — отмена персоналом (нельзя после served).
- `GET /crm/branches/{id}/summary` — счётчики: active_sessions, pending/
  cooking/ready orders, unavailable_items, tables.

**Сессии (CRM)**
- `GET /crm/branches/{id}/sessions` (status/table_id/пагинация),
  `GET /crm/sessions/{id}` (участники + заказы), `POST /crm/sessions/{id}/close`,
  `GET .../participants`, `POST .../participants/{pid}/decide` —
  CRM-подтверждение участника, если хост не отвечает.

**Гость (дополнено)**
- `PATCH /public/sessions/{id}/participants/me` — смена имени.
- `POST /public/sessions/{id}/participants/me/leave` — выход (хосту запрещён,
  он закрывает сессию).
- `GET /public/sessions/{id}/orders/{oid}` — контрактный путь деталки заказа.
- `POST /public/sessions/{id}/orders/{oid}/cancel` — отмена гостем
  (свой заказ или хостом любой; только до кухни: pending/approved).

**KDS**
- `GET /kds/branches/my` — филиалы, доступные кухне.
- KDS-ответы — компактный `KdsOrder` DTO (id, table_title, table_zone, status,
  created_at, items[{title_snapshot, quantity, comment, status}]) — без
  CRM-полей (сумм, модерации).
- `GET /kds/branches/{id}/orders/{oid}` — деталка; `POST .../served` — выдача
  из KDS (в дополнение к CRM served).

**Проверка**: `tests/test_flow.py` — сквозной сценарий на ~40 проверок
(auth → CRM CRUD → каталог → mCafe → заказы → модерация → KDS → официант →
все фичи 2C → формат ошибок → refresh/logout). Запуск:
`rm -f db.sqlite3* && python -m tests.test_flow` → `ALL CHECKS PASSED`.

---

## Осознанные отклонения от контракта

1. **Деньги**: `price_minor`/`total_minor` в тыйынах (int), а не `price` в сомах —
   решение зафиксировано (инвариант CLAUDE.md). Фронт делит на 100.
2. **Картинки**: отдельный `POST /crm/uploads` + URL в JSON-теле CRUD, а не
   multipart-формы в каждом create/update. Правило контракта «фронт не шлёт
   выдуманный URL, backend возвращает URL» соблюдено; сами формы остались JSON.
3. **Идентификация гостя**: `X-Device-Token` (исторический) вместо
   `X-Participant-Token`; скан — `POST /public/sessions/scan`
   (а не `/public/tables/scan`); поле `display_name` (а не `participant_name`).
4. **`type_codes` vs `type_ids`**: в БД и CRM-формах — `type_codes`
   (список строковых кодов); в публичном API отдаётся как `type_ids` по
   контракту. При желании можно переименовать и в CRM.
5. **Order**: `moderation_status` отдельным полем нет — модерация выражена
   основным `status` (pending/approved/rejected), как в исходной архитектуре.
   `moderated_at` не хранится (есть `updated_at` и `moderated_by`).
6. **CRM CRUD для restaurant-types** не делали — контракт explicitly разрешает
   seed-данные («backend может завести эти типы seed-данными»).
7. **Фильтры списков**: реализованы основные (search, status, is_active,
   is_published, city, type_ids, category_id, table_id, is_available);
   `created_at_from/to`, `sort_by/sort_order` — этап 3.
8. **KDS item-level статусы**: статус позиции = статус заказа (контракт
   допускает: «На базовом этапе статусы можно менять на уровне заказа»).
9. **`/crm/branches/my`** — эквивалент живёт на `/crm/me/branches`
   (для kitchen — `/kds/branches/my`).
10. **`GET /auth/login` ответ** — только токены; профиль фронт берёт из
    `/auth/me` (соответствует контрактному frontend behavior).

## Известные ограничения (dev-режим)

- Схема БД создаётся `generate_schemas=True`; Aerich-миграций нет — при
  изменении моделей базу нужно пересоздавать (`rm db.sqlite3*`).
- Файлы хранятся локально в `uploads/` (S3 — на боевом деплое).
- Фронт поллит `/moderation` и `/kds` (WebSocket/SSE — следующая фаза).
- `POST /auth/reg` — внутренний легаси-эндпоинт; создание пользователей
  в проде должно идти через `/crm/users`.

---

## План этапа 3

Приоритет 1 — довести контракт до 100%:
1. **Полные фильтры и сортировка**: `created_at_from/to`, `updated_at_from/to`,
   `sort_by`, `sort_order` на всех списках (общая зависимость рядом с
   `PageParams`); csv-массивы `statuses=...`.
2. **`moderated_at`** на Order + отражение `moderation_status` в сериализации
   (вычисляемое от status) — чтобы CRM-фронт мог читать поля из контракта 7.11.
3. **CRM restaurant-types CRUD** (super_admin) — если admin UI всё же понадобится.
4. **Отдать заказ/сессию по контрактным полям**: `total` (алиас `total_minor`),
   `quantity` (алиас `qty`) в CRM-ответах — согласовать с фронтом единый словарь.

Приоритет 2 — инфраструктура:
5. **Aerich-миграции** в рабочий цикл (конфиг уже заготовлен в
   `config/tortoise_config.py`) — прекратить пересоздание БД.
6. **PostgreSQL** в docker-compose для dev-parity с продом.
7. **S3-хранилище** картинок за интерфейсом (локальный диск как fallback).
8. **Чистка протухших refresh-токенов** (периодическая задача или при login).

Приоритет 3 — следующие продуктовые фазы (по CLAUDE.md):
9. **WebSocket/SSE** для очереди модерации и KDS вместо поллинга.
10. **Item-level статусы KDS** + маршрутизация по `cooking_zone` (бар/кухня).
11. **Архивация вместо удаления** (status=archived уже есть у Company/Branch;
    перевести DELETE на архивацию при наличии связанных данных).
12. **Аудит-лог действий** (super_admin «может видеть системные данные»).
13. **Тесты**: разбить монолитный `tests/test_flow.py` на pytest-модули
    с фикстурами (httpx + ASGITransport паттерн сохранить).
14. Обновить **CLAUDE.md** под новую архитектуру (роли, namespace, форматы).

Не входит (зафиксировано контрактом): онлайн-оплата, фискализация, mobile,
локализация, бонусы/доставка/бронирование, сложные модификаторы блюд.
