# CLAUDE.md — контекст проекта QMenu Backend

Этот файл Claude Code читает автоматически при работе в репозитории. Здесь — стек,
архитектура, инварианты и правила, которые нужно соблюдать при любых изменениях.

## О проекте

QMenu — backend для QR-меню заведений общепита. Гость сканирует QR на столе, делает
заказ, заказ проходит модерацию официантом, попадает на кухню (KDS). Логика стола —
в стиле **mCafe**: первый отсканировавший становится хостом и подтверждает остальных.

## Стек

- **Python 3.12**, **FastAPI**, **Tortoise ORM**, PostgreSQL (в разработке — SQLite).
- Pydantic v2. JWT-авторизация (PyJWT), пароли — bcrypt.
- Конфиг через `python-decouple` (`.env`).
- Схема БД создаётся `generate_schemas=True` при старте. **Aerich-миграций пока нет**
  (конфиг `config/tortoise_config.py` заготовлен, но не подключён к рабочему циклу).

Важно: Tortoise, **не SQLAlchemy**. Нет сессий/Unit of Work — модель сама себя
сохраняет (`await obj.save()`, `Model.create(...)`, `Model.filter(...)`). Связи
ленивые — на списках используем `prefetch_related`, чтобы не ловить N+1.

## Архитектура (слои)

Каждый домен — пакет из трёх слоёв (Repository + Service):

```
app/<домен>/
├── repository.py   только запросы к БД (Tortoise). Никакой бизнес-логики.
├── service.py      бизнес-правила, проверки доступа, HTTPException.
└── urls.py         эндпоинты FastAPI, зависимости авторизации.
```

Общее:
- `app/models/` — ORM-модели (структура таблиц). Pydantic-схемы `Get*`/`Create*`
  генерируются в `app/models/__init__.py` **после** `Tortoise.init_models(...)`.
- `app/common/` — `schemas.py` (Pydantic-схемы запросов), `security.py` (гварды и
  токены), `roles.py` (фиксированный справочник ролей + сидирование).
- `app/router.py` — сборка всех роутеров под префиксом `/api/v1`.
- `main.py` — приложение, CORS, `lifespan` (сидирует роли и admin), Tortoise.

Поток запроса: `urls → service → repository → models → БД`.

Домены: `users`, `companies` (Company+Branch), `menu`, `tables`, `staff`,
`sessions`, `orders`.

## Модель данных (12 таблиц)

```
Role · User
Company (owner=User) → Branch (moderation_mode: strict|soft)
Branch → Employee (User+Role), MenuCategory → MenuItem, Table (qr_token)
Table → TableSession (open|closed) → SessionParticipant (host|pending|approved|rejected)
TableSession → Order (pending→approved→cooking→ready→served | rejected) → OrderItem
```

Решения по привязкам (НЕ менять без явной задачи):
- **Сессия — на стол** (общий чек), но у `Order` есть `participant` → видно, кто
  что заказал (гибрид).
- **Меню — на филиал** (`MenuCategory.branch`).
- **Модерация — это статус заказа** (`Order.pending`), отдельной таблицы-очереди нет.
  Кухня (KDS) видит только `approved/cooking/ready`. Очередь официанта = фильтр
  `status=pending` по филиалу.

## Инварианты — соблюдать в любом коде

1. **Деньги — в тыйынах** (`price_minor`, `total_minor`: `int`). 420.00 сом = 42000.
   Никаких float для денег.
2. **Цена считается только на backend.** Что бы фронт ни прислал — сумма берётся
   из `MenuItem.price_minor`, не из тела запроса.
3. **Снимок в `OrderItem`** (`title_snapshot`, `price_minor`): изменение меню не
   меняет уже созданные заказы. Не заменять на «живую» ссылку на цену.
4. **Проверка принадлежности филиалу** во всех действиях с заказом:
   `order.session.table.branch_id == branch_id`. Нарушение → 404. Касается
   approve/reject/cooking/ready/served и order detail.
5. **Menu item при создании заказа** должен быть из того же филиала, что и стол;
   не в стоп-листе (`is_in_stoplist`); `qty > 0`. Валидировать ВСЕ позиции до
   создания заказа (не создавать «половину заказа»).
6. **mCafe-логика**: первый скан стола → участник `host`; остальные → `pending`;
   заказы могут делать только `host`/`approved` (`SessionParticipant.CAN_ORDER`).
   `host` хранится как `TableSession.host_participant_id` (**int, не FK**) —
   намеренно, чтобы избежать циклической FK-зависимости
   `TableSession ↔ SessionParticipant` (иначе Tortoise не создаёт схему).
7. **Переходы статусов заказа** — только по таблице `TRANSITIONS` в
   `app/orders/service.py`. Недопустимый переход → 409.
8. **Секреты не в коде.** `SECRET_KEY`, `DB_URL`, `PUBLIC_BASE_URL` — через `.env`.

## Авторизация

- Персонал: JWT (`Authorization: Bearer`). Гость: анонимный `X-Device-Token`
  (сервер выдаёт на первом `POST /sessions/scan`).
- Гварды в `app/common/security.py`:
  - `require_branch_owner` — владелец компании филиала (bootstrap-операции: staff).
  - `require_manage(*roles)` — владелец **или** сотрудник с ролью (меню, столы).
  - `require_staff_action(*roles)` — как выше, но возвращает `employee_id`
    (или `None` для владельца) для фиксации исполнителя модерации.
  - `optional_current_user` — JWT необязателен (order detail: гость ИЛИ персонал).
- Роли фиксированные: `owner, admin, manager, senior_waiter, waiter, kitchen`.
  Произвольного конструктора прав НЕТ (решение по ТЗ). Роль-систему пока не
  усложнять без явной задачи.

Важный нюанс bootstrap: владелец компании управляет меню/столами/персоналом ещё
**не будучи** записью в `employee`. Поэтому CRM-эндпоинты проверяют владельца
компании ИЛИ сотрудника — не только `employee`.

## Команды

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r req.txt
uvicorn main:app --reload        # Swagger: http://127.0.0.1:8000/docs
```

Стартовый пользователь `admin / admin` создаётся в `lifespan`.

Тесты: отдельного раннера пока нет. Проверяем через ASGI напрямую
(`httpx.AsyncClient` + `ASGITransport(app=main.app)`) — есть готовый паттерн
end-to-end проверки всего флоу (login → CRUD → mCafe → модерация → KDS).
При добавлении логики — дописывать такую проверку по образцу.

## Стиль

- Строгая типизация (Pydantic v2, аннотации). Docstring на модуль/сложную функцию.
- Repository — только БД; Service — логика и `HTTPException`; urls — тонкие.
- Имена репозиториев осмысленные (`CompanyRepository`, не общий `TortoiseRepository`).
- Ошибки: сейчас стандартный FastAPI `{"detail": "..."}`. Единый формат с `code`
  пока не вводили — если понадобится, добавлять exception handler централизованно.

## Осторожно / не делать без явной задачи

- **Не менять модели в `app/models/`** «между делом» — это меняет схему БД, а
  миграций Aerich ещё нет, база пересоздаётся. Любая правка модели — только осознанно.
- Не ослаблять проверки доступа (branch, host, роли) ради упрощения.
- Не подключать S3 сейчас — фото пока строкой `photo_url` (S3 на боевом деплое).
- Не добавлять WebSocket/SSE, онлайн-оплату, отчёты — это следующие фазы, не текущая.
- Не заменять тыйыны на float; не убирать снапшоты цен в OrderItem.

## Что НЕ реализовано (фазы позже)

Онлайн-оплата (Finik/Optima), фискализация (ОФД/ГНС), WebSocket/SSE (сейчас фронт
поллит `/moderation` и `/kitchen`), pagination, soft-delete, налоговый модуль,
S3 для фото, Aerich-миграции в рабочем цикле.
