# QMENU — Backend API

QR-меню для заведений общепита: гость сканирует QR на столе, делает заказ,
заказ проходит модерацию официантом и уходит на кухню. Логика стола — в стиле
**mCafe**: первый отсканировавший становится хостом и подтверждает остальных.

Стек: **FastAPI + Tortoise ORM + PostgreSQL/SQLite**.

---

## Иерархия данных

```
Role (фиксированные роли)
Company (компания, владелец = User)
└── Branch (филиал/заведение, moderation_mode: strict|soft)
    ├── Employee (User + Role в этом филиале)
    ├── MenuCategory
    │   └── MenuItem (цена в тыйынах, стоп-лист)
    └── Table (qr_token)
        └── TableSession (визит: open|closed)
            ├── SessionParticipant (host|pending|approved|rejected, device_token)
            └── Order (pending→approved→cooking→ready→served | rejected)
                └── OrderItem (снимок названия и цены)
```

Привязки (решения по ТЗ):
- **Сессия — на стол** (один общий чек), но у каждого `Order` есть `participant` —
  видно, кто что заказал (гибрид).
- **Меню — на филиал** (у каждого заведения свои позиции и цены).
- **Модерация — это статус заказа** (`pending`), отдельной таблицы-очереди нет.
  Кухня (KDS) видит только `approved/cooking/ready`. Очередь официанта =
  фильтр `status=pending` по филиалу.

## Архитектура (слои)

Каждый домен — пакет из трёх слоёв (паттерн Repository + Service):

```
app/<домен>/
├── repository.py   только запросы к БД (Tortoise)
├── service.py      бизнес-правила, проверки доступа
└── urls.py         эндпоинты FastAPI
```

`app/models/` — ORM-модели (как таблица выглядит в БД).
`app/common/` — общие схемы запросов, утилиты безопасности, справочник ролей.

Поток запроса: `urls → service → repository → models → БД`.

## Роли (фиксированные)

`owner` · `admin` · `manager` · `senior_waiter` · `waiter` · `kitchen`.
Произвольного конструктора прав нет (решение по ТЗ). Сидируются при старте.

Доступ:
- Управление меню / столами — владелец компании **или** `admin/manager`.
- Назначение сотрудников — только владелец компании.
- Модерация заказов — `admin/manager/senior_waiter/waiter` (и владелец).
- KDS — `admin/manager/senior_waiter/kitchen` (и владелец).

## Логика стола (mCafe)

1. Гость A сканирует QR (`POST /sessions/scan`) → создаётся сессия,
   A становится **host**. Сервер возвращает `device_token` — клиент его хранит
   и шлёт в заголовке `X-Device-Token`.
2. Гость B сканирует тот же QR → участник `pending`.
3. Хост подтверждает B (`POST /sessions/{id}/decide`) → B `approved`.
4. Заказы могут делать только `host` и `approved` участники.
5. Заказ создаётся со статусом `pending` → официант подтверждает/отклоняет →
   на кухню уходит только подтверждённый.

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r req.txt
uvicorn main:app --reload
```

По умолчанию БД — SQLite (`db.sqlite3`), схема создаётся автоматически
(`generate_schemas=True`). Для PostgreSQL заполните `DB_URL` в `config/settings.py`
или через `.env` (см. `.env.example`).

Стартовый пользователь: **admin / admin** (создаётся при первом запуске).

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`

## Миграции (Aerich)

`generate_schemas=True` удобен для разработки, но в проде нужны миграции:

```bash
pip install aerich
aerich init -t config.tortoise_config.TORTOISE_ORM
aerich init-db                 # первая инициализация
aerich migrate --name change   # после изменения моделей
aerich upgrade                 # применить
```

## Карта эндпоинтов (`/api/v1`)

| Группа | Метод | Путь | Кто |
|---|---|---|---|
| Users | POST | `/user/reg` · `/user/login` · GET `/user/me` | публично / JWT |
| Companies | GET·POST·DELETE | `/companies/...` | владелец |
| Branches | GET·POST·PATCH·DELETE | `/companies/{id}/branches/...` | владелец |
| Menu (упр.) | CRUD | `/menu/branches/{id}/categories`, `/items` | owner / manage |
| Menu (гость) | GET | `/menu/branches/{id}/public-menu` | публично |
| Tables | GET·POST·DELETE | `/tables/branches/{id}/tables` | owner / manage |
| Staff | GET·POST·DELETE | `/staff/branches/{id}/employees` | владелец |
| Sessions | POST | `/sessions/scan` | гость (device_token) |
| Sessions | GET·POST | `/sessions/{id}/state·participants·decide·close` | гость / хост |
| Orders (гость) | POST·GET | `/orders/sessions/{id}/orders` | участник |
| Moderation | GET·POST | `/orders/branches/{id}/moderation`, `.../approve`, `.../reject` | официант |
| KDS | GET·POST | `/orders/branches/{id}/kitchen`, `.../cooking`, `.../ready`, `.../served` | кухня |

## Заметки по реализации

- **Цены — в тыйынах** (`price_minor: int`): 420.00 сом = 42000. Никаких float.
- **Снимок цены/названия** в `OrderItem`: изменение меню не меняет старые чеки.
- **host хранится как `host_participant_id` (int)**, а не FK — чтобы избежать
  циклической FK-зависимости `TableSession ↔ SessionParticipant`
  (Tortoise не генерит схему при циклах).
