# QMenu Web Backend Product Contract

Документ фиксирует согласованный базовый backend-контракт для web-части QMenu.

Цель: backend должен закрывать полный понятный flow для `CRM Web`, `Guest Web` и `KDS Web`, а не только минимальные CRUD-таблицы.

## 1. Что входит в текущий scope

### Входит

- CRM Web для управления компаниями, филиалами, меню, столами, сотрудниками и заказами.
- Guest Web для публичного каталога заведений, preview-меню, QR-сессии стола, корзины на frontend и отправки заказа.
- KDS Web для кухни: просмотр заказов и смена статусов приготовления.
- Авторизация для CRM/KDS: `login`, `me`, `refresh`, `logout`.
- Пагинация и фильтры для всех списков.
- Пользовательский формат ошибок, включая ошибки под конкретными полями формы.
- Загрузка картинок через `multipart/form-data`.

### Не входит сейчас

- Mobile-приложение.
- Официант и manager в mobile.
- Онлайн-оплата.
- Локализация.
- Отдельная сущность `Media`.
- Бонусы, cashback, рейтинг заведений, карта, доставка, бронирование.
- Сложные модификаторы блюд.

## 2. Роли

### `super_admin`

Интерфейс: CRM Web.

Главный администратор платформы QMenu.

Функционал:

- видит все компании;
- создает компании;
- редактирует компании;
- удаляет или архивирует компании;
- создает, редактирует и удаляет филиалы любой компании;
- управляет меню, категориями, блюдами, столами, сотрудниками и заказами любого филиала;
- назначает владельцев компаний;
- назначает администраторов филиалов;
- может видеть системные данные, если позже появится журнал действий.

Почему нужна роль:

- QMenu является платформой, а не CRM одной компании;
- должен быть пользователь, который не привязан к конкретному ресторану;
- backend должен проверять доступ на уровне всей системы.

### `owner`

Интерфейс: CRM Web.

Владелец компании или сети заведений.

Функционал:

- видит только свои компании;
- редактирует данные своих компаний;
- создает филиалы внутри своих компаний;
- редактирует филиалы своих компаний;
- удаляет или архивирует филиалы своих компаний;
- управляет меню своих филиалов;
- управляет категориями блюд;
- управляет блюдами;
- управляет столами и QR;
- управляет сотрудниками своих филиалов;
- назначает `branch_admin` и `kitchen`;
- смотрит и модерирует заказы своих филиалов.

Ограничения:

- не видит чужие компании;
- не назначает `super_admin`;
- не управляет платформенными настройками;
- не удаляет собственную компанию, если это запрещено бизнес-правилом.

Почему нужна роль:

- владелец отвечает за свой бизнес;
- у сети может быть несколько филиалов;
- владелец не должен иметь доступ к чужим данным.

### `branch_admin`

Интерфейс: CRM Web.

Администратор одного или нескольких филиалов.

Функционал:

- видит только назначенные ему филиалы;
- открывает деталку своего филиала;
- редактирует операционные данные филиала, если разрешено;
- управляет категориями меню филиала;
- управляет блюдами филиала;
- управляет столами и QR филиала;
- смотрит заказы филиала;
- подтверждает или отклоняет заказы, если включена строгая модерация;
- может добавлять сотрудников низшего уровня только если это разрешено правилами доступа.

Ограничения:

- не создает компании;
- не удаляет компании;
- не создает филиалы;
- не удаляет филиалы;
- не назначает `owner`;
- не назначает `super_admin`;
- не видит чужие филиалы.

Почему нужна роль:

- администратор филиала работает внутри конкретной точки;
- ему не нужен доступ к всей компании;
- эта роль закрывает web CRM без mobile manager.

### `guest`

Интерфейс: Guest Web.

Публичный пользователь.

Функционал до QR:

- открывает главную guest-зоны;
- смотрит список заведений;
- ищет заведения;
- фильтрует заведения по типу;
- открывает деталку заведения;
- смотрит филиалы;
- открывает preview-меню филиала;
- смотрит категории и блюда.

Функционал после QR:

- попадает в сессию конкретного стола;
- становится host или участником;
- видит меню конкретного филиала;
- добавляет блюда в корзину;
- отправляет заказ;
- видит статусы заказов;
- видит участников текущего стола.

Ограничения:

- не может отправить заказ без QR-сессии;
- не имеет CRM-доступа;
- не видит внутренние данные ресторана.

Почему нужна роль:

- это основной клиентский сценарий QMenu;
- guest не должен устанавливать приложение.

### `kitchen`

Интерфейс: KDS Web.

Сотрудник кухни.

Функционал:

- видит заказы своего филиала;
- видит стол, зону, время создания и позиции;
- берет заказ в работу;
- отмечает заказ готовым;
- отмечает заказ выданным, если этот шаг нужен в KDS flow.

Ограничения:

- не управляет компаниями;
- не управляет филиалами;
- не редактирует меню;
- не управляет сотрудниками;
- не видит чужие филиалы.

Почему нужна роль:

- кухня должна работать в отдельном простом интерфейсе;
- KDS не должен быть перегружен CRM-функциями.

## 3. Access matrix

| Сущность | super_admin | owner | branch_admin | guest | kitchen |
| --- | --- | --- | --- | --- | --- |
| Companies | all CRUD | own read/update | no | public read only | no |
| Branches | all CRUD | own CRUD | assigned read/update limited | public read only | assigned read |
| Restaurant types | all/manage or read | read | read | read | no |
| Categories | all CRUD | own branches CRUD | assigned branches CRUD | read public | no |
| Menu items | all CRUD | own branches CRUD | assigned branches CRUD | read public/order after QR | read for KDS |
| Tables | all CRUD | own branches CRUD | assigned branches CRUD | scan only | no |
| Sessions | all read/manage | own branches read/manage | assigned read/manage | own session only | no |
| Orders | all read/manage | own branches read/manage | assigned read/manage | own session only | assigned KDS actions |
| Employees | all manage | own company manage | limited branch manage | no | no |

## 4. Общие правила API

### Base URL

Все endpoint располагаются под:

```txt
/api/v1
```

Рекомендуемое разделение:

```txt
/api/v1/auth/*
/api/v1/crm/*
/api/v1/public/*
/api/v1/kds/*
```

Почему:

- `auth` обслуживает CRM и KDS;
- `crm` требует авторизации и прав;
- `public` доступен guest без CRM-токена;
- `kds` можно развивать отдельно от CRM.

### Response wrapper

Для mutation/detail ответов:

```json
{
  "success": true,
  "message": "OK",
  "data": {}
}
```

Для списков:

```json
{
  "data": [],
  "pagination": {
    "current_page": 1,
    "last_page": 5,
    "per_page": 20,
    "total": 95
  }
}
```

Почему:

- frontend единообразно читает `data`;
- списки сразу готовы для AntD Table;
- `pagination.total` нужен для отображения общего количества.

### Pagination request

Каждый list endpoint должен принимать:

```txt
limit=20
offset=0
page=1
```

`offset`:

```txt
offset = (page - 1) * limit
```

Пример:

```txt
GET /api/v1/crm/companies?limit=20&page=2&offset=20
```

Backend может вычислять offset сам по `page` и `limit`, но frontend будет передавать их явно.

### Common filters

Базовые фильтры для списков:

```txt
search
status
is_active
is_published
created_at_from
created_at_to
updated_at_from
updated_at_to
sort_by
sort_order
limit
offset
page
```

`sort_order`:

```txt
asc | desc
```

Boolean передается строкой:

```txt
is_active=true
is_published=false
```

Массивы передаются строкой через запятую:

```txt
type_ids=coffee,restaurant
statuses=pending,approved
```

Почему:

- URL можно сохранять и шарить;
- фильтры легко синхронизируются с query params;
- frontend не должен держать фильтры только во внутреннем состоянии.

### Date format

Все даты в ответах:

```txt
ISO 8601
```

Пример:

```json
"created_at": "2026-06-30T10:00:00Z"
```

### Money format

В базовом scope цена хранится целым числом в сомах:

```json
"price": 520
```

Почему:

- не усложняем валютами и оплатой;
- guest и CRM сейчас показывают простую цену.

### Image upload

Картинки frontend отправляет как `File` через:

```txt
Content-Type: multipart/form-data
```

Backend сохраняет файл и возвращает URL:

```json
{
  "image_url": "https://..."
}
```

Правила:

- frontend не отправляет вручную написанный URL;
- `logo`, `cover`, `image` в request являются файлами;
- `logo_url`, `cover_url`, `image_url` в response являются строками;
- при `PATCH` файл необязательный;
- если файл не отправлен, старая картинка остается.

## 5. Формат ошибок

Backend должен возвращать текст, который можно показать пользователю.

Технические детали, stack trace, SQL errors и raw exception messages не должны уходить на frontend.

### General error

```json
{
  "success": false,
  "message": "Не удалось выполнить действие",
  "code": "ACTION_FAILED"
}
```

Поля:

| Поле | Формат | Зачем |
| --- | --- | --- |
| `success` | boolean | frontend понимает, что действие завершилось ошибкой |
| `message` | string | текст для notification/modal |
| `code` | string | машинный код для редких специальных обработок |

### Validation error

```json
{
  "success": false,
  "message": "Проверьте поля формы",
  "code": "VALIDATION_ERROR",
  "field_errors": {
    "title": ["Введите название"],
    "cover": ["Загрузите обложку"],
    "price": ["Цена должна быть больше 0"]
  }
}
```

Поля:

| Поле | Формат | Зачем |
| --- | --- | --- |
| `message` | string | общий текст ошибки формы |
| `field_errors` | object | ошибки под конкретными полями AntD Form |
| `field_errors.title` | string[] | frontend показывает текст под `title` |
| `field_errors.cover` | string[] | frontend показывает текст под upload-полем |

Правило:

- ключи в `field_errors` должны совпадать с именами полей request;
- текст должен быть пользовательским;
- одна ошибка поля тоже возвращается массивом.

### Auth error

```json
{
  "success": false,
  "message": "Неверный логин или пароль",
  "code": "INVALID_CREDENTIALS"
}
```

### Permission error

```json
{
  "success": false,
  "message": "У вас нет доступа к этому разделу",
  "code": "FORBIDDEN"
}
```

### Not found error

```json
{
  "success": false,
  "message": "Запись не найдена",
  "code": "NOT_FOUND"
}
```

## 6. Auth flow

Auth нужен для CRM Web и KDS Web.

Guest Web не требует login.

### `POST /api/v1/auth/login`

Назначение:

- авторизация CRM/KDS пользователя;
- выдача access/refresh tokens.

Request:

```json
{
  "login": "owner",
  "password": "password"
}
```

Поля request:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `login` | string | yes | единое поле для логина/email/phone, чтобы frontend не зависел от способа входа |
| `password` | string | yes | пароль пользователя |

Response:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "access_token": "jwt-access",
    "refresh_token": "jwt-refresh"
  }
}
```

Поля response:

| Поле | Формат | Зачем |
| --- | --- | --- |
| `access_token` | string | используется в `Authorization` для обычных запросов |
| `refresh_token` | string | используется для обновления access token |

Frontend behavior:

1. отправляет login/password;
2. сохраняет `access_token` и `refresh_token`;
3. вызывает `GET /api/v1/auth/me`;
4. строит доступные routes/sidebar по роли и scopes;
5. редиректит пользователя на первый доступный раздел.

### `GET /api/v1/auth/me`

Назначение:

- получить текущего пользователя;
- получить роль;
- получить company/branch scopes;
- получить permissions.

Headers:

```txt
Authorization: Bearer <access_token>
```

Response:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "id": 1,
    "login": "owner",
    "full_name": "Owner User",
    "role": "owner",
    "roles": ["owner"],
    "company_ids": [1],
    "branch_ids": [11, 12],
    "permissions": [
      "companies.read",
      "companies.update",
      "branches.manage",
      "menu.manage",
      "tables.manage",
      "staff.manage",
      "orders.manage"
    ]
  }
}
```

Поля:

| Поле | Формат | Зачем |
| --- | --- | --- |
| `id` | number | идентификатор пользователя |
| `login` | string | отображение в профиле/хедере |
| `full_name` | string | человекочитаемое имя в CRM |
| `role` | string | основная роль для простого route access |
| `roles` | string[] | поддержка нескольких ролей, если понадобится |
| `company_ids` | number[] | ограничение owner по компаниям |
| `branch_ids` | number[] | ограничение branch_admin/kitchen по филиалам |
| `permissions` | string[] | точечные права для sidebar/actions |

Почему `me` должен быть полным:

- frontend не должен угадывать роль;
- backend остается источником прав;
- `branch_admin` должен видеть только назначенные филиалы;
- `kitchen` не должен попасть в CRM-страницы.

### `POST /api/v1/auth/refresh`

Назначение:

- обновить токены после `401`.

Headers:

```txt
Authorization: Bearer <refresh_token>
```

Response:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "access_token": "new-access-token",
    "refresh_token": "new-refresh-token"
  }
}
```

Frontend behavior:

1. обычный запрос получает `401`;
2. frontend вызывает refresh;
3. если refresh успешен, frontend повторяет исходный запрос;
4. если refresh неуспешен, frontend чистит токены и ведет на `/admin/login`.

### `POST /api/v1/auth/logout`

Назначение:

- завершить backend-сессию или инвалидировать refresh token.

Headers:

```txt
Authorization: Bearer <refresh_token>
```

Response:

```json
{
  "success": true,
  "message": "Вы вышли из системы",
  "data": null
}
```

Frontend behavior:

- вызывает logout;
- чистит токены в любом случае;
- сбрасывает API cache;
- редиректит на login.

## 7. Сущности и поля

### 7.1 User

Назначение: пользователь системы, который может быть owner, branch_admin, kitchen или super_admin.

```ts
User {
  id: number
  login: string
  full_name: string
  phone?: string
  role: UserRole
  roles: UserRole[]
  company_ids: number[]
  branch_ids: number[]
  is_active: boolean
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | все связи | основной идентификатор пользователя |
| `login` | string | yes | auth, CRM header, staff search | логин для входа и поиска |
| `full_name` | string | yes | CRM, staff table | человекочитаемое имя |
| `phone` | string | no | staff table/search | дополнительная идентификация сотрудника |
| `role` | enum | yes | route guard, sidebar | основная роль пользователя |
| `roles` | enum[] | yes | future-safe auth | если позже будет несколько ролей |
| `company_ids` | number[] | yes | owner access | компании, к которым есть доступ |
| `branch_ids` | number[] | yes | branch_admin/kitchen access | филиалы, к которым есть доступ |
| `is_active` | boolean | yes | login/access checks | можно отключить пользователя без удаления |
| `created_at` | ISO string | yes | CRM audit/display | дата создания |
| `updated_at` | ISO string | yes | CRM audit/display | дата последнего изменения |

### 7.2 Company

Назначение: ресторанный бренд или сеть заведений. На guest-главной отображается как карточка заведения.

```ts
Company {
  id: number
  slug: string
  title: string
  description: string
  short_description: string
  type_ids: string[]
  type_title: string
  logo_url: string
  cover_url: string
  owner_id: number
  status: 'draft' | 'active' | 'archived'
  is_active: boolean
  is_published: boolean
  branches_count: number
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | CRM routes, relations | внутренний идентификатор |
| `slug` | string | yes | Guest URL | красивый public URL: `/guest/places/navat` |
| `title` | string | yes | CRM, Guest cards/details | название заведения |
| `description` | string | yes | Guest detail | полное описание заведения |
| `short_description` | string | yes | Guest cards | короткий текст в карточке |
| `type_ids` | string[] | yes | Guest filters, CRM filters | фильтрация: кофейня, ресторан, чайхана |
| `type_title` | string | yes | Guest card badge | готовый текст типов для UI |
| `logo_url` | string | yes | Guest card/detail | логотип заведения |
| `cover_url` | string | yes | Guest card/detail | большая картинка заведения |
| `owner_id` | number | yes | CRM access | привязка владельца |
| `status` | enum | yes | CRM lifecycle | draft/active/archive без физического удаления |
| `is_active` | boolean | yes | CRM/backend access | включение/отключение компании |
| `is_published` | boolean | yes | Guest public list | можно создать в CRM, но пока не показывать гостям |
| `branches_count` | number | yes | CRM/Guest cards | быстро показать количество филиалов |
| `created_at` | ISO string | yes | CRM table | дата создания |
| `updated_at` | ISO string | yes | CRM table | дата изменения |

Create/Update format:

```txt
multipart/form-data

title: string
description: string
short_description: string
type_ids: coffee,restaurant
owner_id: number
logo: File
cover: File
is_published: boolean
is_active: boolean
```

Почему FormData:

- логотип и обложка загружаются как реальные файлы;
- backend сам сохраняет файлы и возвращает URL.

### 7.3 RestaurantType

Назначение: справочник типов заведений для фильтров и карточек.

```ts
RestaurantType {
  id: number
  code: string
  title: string
  image_url: string
  sort_order: number
  is_active: boolean
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | CRM relation | внутренний id |
| `code` | string | yes | filters/query | стабильный код: `coffee`, `restaurant` |
| `title` | string | yes | Guest filters | название типа |
| `image_url` | string | yes | Guest category chips | картинка/иконка типа |
| `sort_order` | number | yes | Guest filters order | порядок отображения |
| `is_active` | boolean | yes | public filters | скрыть тип без удаления |

Примеры `code`:

```txt
coffee
chaikhana
restaurant
fastfood
pizza
sushi
```

### 7.4 Branch

Назначение: конкретная ресторанная точка внутри компании.

```ts
Branch {
  id: number
  company_id: number
  slug: string
  title: string
  address: string
  city: string
  latitude?: number
  longitude?: number
  phone?: string
  cover_url: string
  working_hours: string
  schedule: BranchScheduleDay[]
  is_open: boolean
  moderation_mode: 'strict' | 'auto'
  status: 'draft' | 'active' | 'archived'
  is_active: boolean
  is_published: boolean
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | CRM routes, menu, tables, orders | внутренний id филиала |
| `company_id` | number | yes | relations/access | филиал принадлежит компании |
| `slug` | string | yes | Guest URL | `/guest/places/navat/branches/navat-chui-35` |
| `title` | string | yes | CRM, Guest, KDS | короткое имя филиала: `Чуй 35` |
| `address` | string | yes | Guest branch card, table session | адрес филиала |
| `city` | string | yes | filters, branch card | город для фильтрации |
| `latitude` | number | no | future map | координаты можно использовать позже |
| `longitude` | number | no | future map | координаты можно использовать позже |
| `phone` | string | no | Guest details/CRM | контакт филиала |
| `cover_url` | string | yes | Guest branch card/menu hero | фото филиала |
| `working_hours` | string | yes | Guest UI | готовый текст: `09:00 - 00:00` |
| `schedule` | array | yes | backend open/closed logic | структурный график работы |
| `is_open` | boolean | yes | Guest badges | сейчас филиал открыт или закрыт |
| `moderation_mode` | enum | yes | orders flow | нужно ли подтверждение заказа |
| `status` | enum | yes | CRM lifecycle | draft/active/archive |
| `is_active` | boolean | yes | CRM/KDS access | включен ли филиал |
| `is_published` | boolean | yes | Guest public pages | показывать ли филиал гостям |
| `created_at` | ISO string | yes | CRM table | дата создания |
| `updated_at` | ISO string | yes | CRM table | дата изменения |

Schedule:

```ts
BranchScheduleDay {
  day_of_week: 1 | 2 | 3 | 4 | 5 | 6 | 7
  opens_at: string
  closes_at: string
  is_closed: boolean
}
```

Поля schedule:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `day_of_week` | number | yes | день недели, 1 - понедельник |
| `opens_at` | `HH:mm` | yes | время открытия |
| `closes_at` | `HH:mm` | yes | время закрытия |
| `is_closed` | boolean | yes | выходной день |

Create/Update format:

```txt
multipart/form-data

title: string
address: string
city: string
latitude?: number
longitude?: number
phone?: string
schedule: JSON string
moderation_mode: strict | auto
cover: File
is_active: boolean
is_published: boolean
```

### 7.5 MenuCategory

Назначение: раздел меню внутри конкретного филиала.

```ts
MenuCategory {
  id: number
  branch_id: number
  slug: string
  title: string
  description?: string
  image_url?: string
  sort_order: number
  is_active: boolean
  is_published: boolean
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | menu item relation | id категории |
| `branch_id` | number | yes | menu scope | меню у каждого филиала свое |
| `slug` | string | yes | optional public anchors | стабильный идентификатор категории |
| `title` | string | yes | Guest menu tabs, CRM table | название категории |
| `description` | string | no | CRM/details | дополнительное описание |
| `image_url` | string | no | future visual categories | картинка категории, если понадобится |
| `sort_order` | number | yes | Guest menu order | порядок категорий |
| `is_active` | boolean | yes | CRM visibility | активна ли категория |
| `is_published` | boolean | yes | Guest visibility | показывать ли гостям |
| `created_at` | ISO string | yes | CRM table | дата создания |
| `updated_at` | ISO string | yes | CRM table | дата изменения |

Create/Update format:

```txt
multipart/form-data

title: string
description?: string
sort_order: number
image?: File
is_active: boolean
is_published: boolean
```

### 7.6 MenuItem

Назначение: блюдо или напиток в меню филиала.

```ts
MenuItem {
  id: number
  branch_id: number
  category_id: number
  title: string
  description: string
  image_url: string
  price: number
  weight?: number
  weight_unit?: 'g' | 'ml' | 'pcs'
  sort_order: number
  status: 'active' | 'hidden' | 'stop_list'
  is_available: boolean
  is_published: boolean
  cooking_zone: 'kitchen'
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | orders/order items | id блюда |
| `branch_id` | number | yes | menu scope | блюдо принадлежит конкретному филиалу |
| `category_id` | number | yes | category grouping | к какой категории относится блюдо |
| `title` | string | yes | Guest menu, KDS, order snapshot | название блюда |
| `description` | string | yes | Guest menu card | состав/описание блюда |
| `image_url` | string | yes | Guest menu card | фото блюда |
| `price` | number | yes | Guest cart/order | цена в сомах |
| `weight` | number | no | Guest menu card | граммовка/объем |
| `weight_unit` | enum | no | Guest menu card | единица измерения |
| `sort_order` | number | yes | Guest menu order | порядок внутри категории |
| `status` | enum | yes | CRM/KDS/Guest visibility | active, hidden или stop-list |
| `is_available` | boolean | yes | Guest order ability | можно ли заказать сейчас |
| `is_published` | boolean | yes | Guest visibility | видно ли гостям |
| `cooking_zone` | enum | yes | KDS filtering | куда отправлять позицию |
| `created_at` | ISO string | yes | CRM table | дата создания |
| `updated_at` | ISO string | yes | CRM table | дата изменения |

Почему `status` и `is_available` оба нужны:

- `status=hidden` - блюдо не показывается гостям;
- `status=stop_list` - блюдо может быть видно, но недоступно;
- `is_available=false` удобно быстро менять доступность.

Create/Update format:

```txt
multipart/form-data

category_id: number
title: string
description: string
price: number
weight?: number
weight_unit?: g | ml | pcs
sort_order: number
status: active | hidden | stop_list
is_available: boolean
is_published: boolean
cooking_zone: kitchen
image?: File
```

### 7.7 Table

Назначение: стол филиала, по QR которого открывается guest session.

```ts
Table {
  id: number
  branch_id: number
  title: string
  number: string
  zone: string
  seats?: number
  qr_token: string
  public_url: string
  is_active: boolean
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | sessions/orders | id стола |
| `branch_id` | number | yes | branch scope | стол принадлежит филиалу |
| `title` | string | yes | CRM, Guest session, KDS | красивое название: `A-5` |
| `number` | string | yes | CRM/KDS | номер стола |
| `zone` | string | yes | CRM/KDS | зал/зона: `Главный зал` |
| `seats` | number | no | CRM | количество мест |
| `qr_token` | string | yes | QR scan | технический токен QR |
| `public_url` | string | yes | CRM copy/print | готовая ссылка для QR |
| `is_active` | boolean | yes | scan validation | отключить стол без удаления |
| `created_at` | ISO string | yes | CRM table | дата создания |
| `updated_at` | ISO string | yes | CRM table | дата изменения |

Create request:

```json
{
  "title": "A-5",
  "number": "A-5",
  "zone": "Главный зал",
  "seats": 4,
  "is_active": true
}
```

### 7.8 TableSession

Назначение: активная сессия гостей за конкретным столом.

```ts
TableSession {
  id: number
  branch_id: number
  table_id: number
  host_participant_id: number
  status: 'open' | 'closed'
  opened_at: string
  closed_at?: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | orders/participants | id сессии |
| `branch_id` | number | yes | orders/KDS | филиал сессии |
| `table_id` | number | yes | Guest/KDS | стол сессии |
| `host_participant_id` | number | yes | participant approval | кто управляет участниками |
| `status` | enum | yes | session lifecycle | открыта или закрыта |
| `opened_at` | ISO string | yes | CRM/session display | когда открыли |
| `closed_at` | ISO string | no | history | когда закрыли |

Почему нужна отдельная сессия:

- один стол используется много раз за день;
- заказы должны относиться к конкретному посещению;
- участники должны быть связаны с конкретной сессией, а не просто со столом.

### 7.9 Participant

Назначение: гость внутри table session.

```ts
Participant {
  id: number
  session_id: number
  name: string
  status: 'host' | 'pending' | 'approved' | 'rejected'
  participant_token: string
  joined_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | orders | id участника |
| `session_id` | number | yes | Guest session | принадлежность к сессии |
| `name` | string | yes | Guest participants/orders | отображаемое имя |
| `status` | enum | yes | guest permissions | host/approved может заказывать |
| `participant_token` | string | yes | public session requests | простой токен текущего guest |
| `joined_at` | ISO string | yes | participants list | когда присоединился |

### 7.10 GuestCart

Корзина не хранится в backend.

Назначение: временное состояние на frontend до отправки заказа.

```ts
GuestCart {
  session_id: number
  branch_id: number
  items: GuestCartItem[]
  total: number
}
```

```ts
GuestCartItem {
  menu_item_id: number
  title: string
  price: number
  image_url: string
  quantity: number
  comment?: string
}
```

Почему не backend-сущность:

- корзина может быть брошена;
- кухня и CRM работают только с отправленными заказами;
- MVP становится проще;
- после submit корзина превращается в `Order`.

### 7.11 Order

Назначение: отправленный гостем заказ.

```ts
Order {
  id: number
  session_id: number
  branch_id: number
  table_id: number
  participant_id: number
  status: 'pending_moderation' | 'approved' | 'cooking' | 'ready' | 'served' | 'rejected' | 'cancelled'
  moderation_status: 'pending' | 'approved' | 'rejected'
  total: number
  comment?: string
  reject_reason?: string
  moderated_by?: number
  moderated_at?: string
  created_at: string
  updated_at: string
  items: OrderItem[]
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | CRM/KDS/Guest | id заказа |
| `session_id` | number | yes | Guest session | связь с сессией стола |
| `branch_id` | number | yes | CRM/KDS scope | филиал заказа |
| `table_id` | number | yes | KDS/CRM | стол заказа |
| `participant_id` | number | yes | Guest/CRM | кто отправил заказ |
| `status` | enum | yes | Guest/KDS/CRM | общий статус заказа |
| `moderation_status` | enum | yes | CRM moderation | ожидает/подтвержден/отклонен |
| `total` | number | yes | Guest/CRM | сумма заказа |
| `comment` | string | no | CRM/KDS | общий комментарий гостя |
| `reject_reason` | string | no | Guest/CRM | почему заказ отклонен |
| `moderated_by` | number | no | CRM audit | кто подтвердил/отклонил |
| `moderated_at` | ISO string | no | CRM audit | когда подтвердили/отклонили |
| `created_at` | ISO string | yes | all order lists | время создания |
| `updated_at` | ISO string | yes | all order lists | время изменения |
| `items` | OrderItem[] | yes | Guest/CRM/KDS | позиции заказа |

### 7.12 OrderItem

Назначение: позиция внутри заказа.

```ts
OrderItem {
  id: number
  order_id: number
  menu_item_id: number
  title_snapshot: string
  price_snapshot: number
  quantity: number
  comment?: string
  cooking_zone: 'kitchen'
  status: 'pending' | 'cooking' | 'ready' | 'served' | 'cancelled'
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | KDS/order detail | id позиции |
| `order_id` | number | yes | relation | связь с заказом |
| `menu_item_id` | number | yes | analytics/link | ссылка на блюдо |
| `title_snapshot` | string | yes | Guest/KDS | название на момент заказа |
| `price_snapshot` | number | yes | totals/history | цена на момент заказа |
| `quantity` | number | yes | all order views | количество |
| `comment` | string | no | KDS | комментарий к позиции |
| `cooking_zone` | enum | yes | KDS | куда отправить позицию |
| `status` | enum | yes | KDS/Guest | статус позиции |

Почему snapshot обязателен:

- если блюдо переименовали или поменяли цену после заказа, старый заказ должен остаться корректным.

### 7.13 Employee

Назначение: связь пользователя с компанией/филиалом и ролью.

```ts
Employee {
  id: number
  user_id: number
  company_id: number
  branch_id?: number
  role: 'owner' | 'branch_admin' | 'kitchen'
  status: 'active' | 'blocked'
  created_at: string
  updated_at: string
}
```

Поля:

| Поле | Формат | Required | Где используется | Зачем |
| --- | --- | --- | --- | --- |
| `id` | number | yes | CRM employee table | id назначения |
| `user_id` | number | yes | relation | какой пользователь назначен |
| `company_id` | number | yes | owner/company scope | компания сотрудника |
| `branch_id` | number | no | branch scope | филиал сотрудника |
| `role` | enum | yes | permissions | роль внутри компании/филиала |
| `status` | enum | yes | access | active/blocked |
| `created_at` | ISO string | yes | CRM | дата назначения |
| `updated_at` | ISO string | yes | CRM | дата изменения |

## 8. CRM API

Все CRM endpoint требуют:

```txt
Authorization: Bearer <access_token>
```

### 8.1 Companies

#### `GET /api/v1/crm/companies`

Назначение: список компаний для CRM.

Роли:

- `super_admin` - все компании;
- `owner` - только свои компании.

Filters:

```txt
search
type_ids
status
is_active
is_published
created_at_from
created_at_to
limit
offset
page
sort_by
sort_order
```

Response:

```ts
PaginationResponse<Company>
```

Почему нужны фильтры:

- `search` - поиск по названию;
- `type_ids` - фильтр по типу заведения;
- `status/is_active/is_published` - отделить черновики, активные и публичные компании;
- pagination - компаний может быть много.

#### `POST /api/v1/crm/companies`

Назначение: создать компанию.

Content-Type:

```txt
multipart/form-data
```

Роли:

- `super_admin`;
- `owner`, если ему разрешено создать свою компанию.

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `title` | string | yes | название компании |
| `description` | string | yes | полное описание для guest detail |
| `short_description` | string | yes | короткое описание для guest card |
| `type_ids` | comma string | yes | типы заведения |
| `owner_id` | number | yes for super_admin | назначить владельца |
| `logo` | File | yes | логотип |
| `cover` | File | yes | обложка |
| `is_published` | boolean | yes | показывать гостям или нет |

#### `GET /api/v1/crm/companies/{company_id}`

Назначение: деталка компании.

Роли:

- `super_admin`;
- `owner` своей компании.

Response:

```ts
ApiResponse<Company>
```

#### `PATCH /api/v1/crm/companies/{company_id}`

Назначение: обновить компанию.

Content-Type:

```txt
multipart/form-data
```

Fields optional:

```txt
title
description
short_description
type_ids
logo
cover
is_active
is_published
```

#### `DELETE /api/v1/crm/companies/{company_id}`

Назначение: удалить или архивировать компанию.

Роли:

- `super_admin`.

Рекомендация: лучше архивировать, а не физически удалять, если у компании есть филиалы, заказы или сотрудники.

### 8.2 Restaurant Types

#### `GET /api/v1/crm/restaurant-types`

Назначение: справочник типов заведений для CRM forms/filters.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
search
is_active
limit
offset
page
```

#### `POST /api/v1/crm/restaurant-types`

Назначение: создать тип заведения.

Роли:

- `super_admin`.

Content-Type:

```txt
multipart/form-data
```

Fields:

```txt
code
title
image
sort_order
is_active
```

Если не хотим усложнять admin UI, backend может завести эти типы seed-данными.

#### `PATCH /api/v1/crm/restaurant-types/{type_id}`

Роли:

- `super_admin`.

#### `DELETE /api/v1/crm/restaurant-types/{type_id}`

Роли:

- `super_admin`.

### 8.3 Branches

#### `GET /api/v1/crm/companies/{company_id}/branches`

Назначение: список филиалов внутри компании.

Роли:

- `super_admin`;
- `owner` своей компании.

Filters:

```txt
search
city
status
is_active
is_published
limit
offset
page
sort_by
sort_order
```

Response:

```ts
PaginationResponse<Branch>
```

#### `GET /api/v1/crm/branches/my`

Назначение: получить филиалы, доступные текущему пользователю.

Роли:

- `owner`;
- `branch_admin`;
- `kitchen`.

Почему нужно:

- `branch_admin` не должен открывать общий список компаний;
- KDS должен знать, какие филиалы доступны кухне.

#### `POST /api/v1/crm/companies/{company_id}/branches`

Назначение: создать филиал.

Content-Type:

```txt
multipart/form-data
```

Роли:

- `super_admin`;
- `owner` своей компании.

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `title` | string | yes | название филиала |
| `address` | string | yes | адрес для guest |
| `city` | string | yes | фильтр и отображение |
| `latitude` | number | no | будущая карта |
| `longitude` | number | no | будущая карта |
| `phone` | string | no | контакт филиала |
| `schedule` | JSON string | yes | график работы |
| `moderation_mode` | enum | yes | flow заказов |
| `cover` | File | yes | фото филиала |
| `is_published` | boolean | yes | показывать гостям |

#### `GET /api/v1/crm/branches/{branch_id}`

Назначение: деталка филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`;
- `kitchen` read-only.

#### `PATCH /api/v1/crm/branches/{branch_id}`

Назначение: обновить филиал.

Content-Type:

```txt
multipart/form-data
```

Роли:

- `super_admin`;
- `owner`;
- `branch_admin` limited fields.

#### `DELETE /api/v1/crm/branches/{branch_id}`

Назначение: удалить или архивировать филиал.

Роли:

- `super_admin`;
- `owner`.

### 8.4 Menu Categories

#### `GET /api/v1/crm/branches/{branch_id}/menu/categories`

Назначение: список категорий меню филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
search
is_active
is_published
limit
offset
page
sort_by
sort_order
```

#### `POST /api/v1/crm/branches/{branch_id}/menu/categories`

Content-Type:

```txt
multipart/form-data
```

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `title` | string | yes | название категории |
| `description` | string | no | описание |
| `sort_order` | number | yes | порядок |
| `image` | File | no | картинка категории |
| `is_active` | boolean | yes | активность |
| `is_published` | boolean | yes | публичность |

#### `GET /api/v1/crm/branches/{branch_id}/menu/categories/{category_id}`

Назначение: деталка категории.

#### `PATCH /api/v1/crm/branches/{branch_id}/menu/categories/{category_id}`

Content-Type:

```txt
multipart/form-data
```

#### `DELETE /api/v1/crm/branches/{branch_id}/menu/categories/{category_id}`

Если в категории есть блюда:

```json
{
  "success": false,
  "message": "Нельзя удалить категорию, в которой есть блюда",
  "code": "CATEGORY_HAS_ITEMS"
}
```

### 8.5 Menu Items

#### `GET /api/v1/crm/branches/{branch_id}/menu/items`

Назначение: список блюд филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
search
category_id
status
is_available
is_published
limit
offset
page
sort_by
sort_order
```

Response:

```ts
PaginationResponse<MenuItem>
```

#### `POST /api/v1/crm/branches/{branch_id}/menu/items`

Назначение: создать блюдо.

Content-Type:

```txt
multipart/form-data
```

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `category_id` | number | yes | связь с категорией |
| `title` | string | yes | название блюда |
| `description` | string | yes | состав/описание |
| `price` | number | yes | цена |
| `weight` | number | no | граммовка/объем |
| `weight_unit` | enum | no | g/ml/pcs |
| `sort_order` | number | yes | порядок |
| `status` | enum | yes | active/hidden/stop_list |
| `is_available` | boolean | yes | доступность |
| `is_published` | boolean | yes | публичность |
| `cooking_zone` | enum | yes | KDS route |
| `image` | File | yes | фото блюда |

#### `GET /api/v1/crm/branches/{branch_id}/menu/items/{item_id}`

Назначение: деталка блюда.

#### `PATCH /api/v1/crm/branches/{branch_id}/menu/items/{item_id}`

Content-Type:

```txt
multipart/form-data
```

#### `DELETE /api/v1/crm/branches/{branch_id}/menu/items/{item_id}`

Назначение: удалить блюдо.

Если блюдо уже было в заказах, лучше архивировать или скрывать, а не физически удалять.

#### `POST /api/v1/crm/branches/{branch_id}/menu/items/{item_id}/availability`

Назначение: быстро включить/выключить блюдо или отправить в stop-list.

Request:

```json
{
  "is_available": false,
  "status": "stop_list"
}
```

### 8.6 Tables

#### `GET /api/v1/crm/branches/{branch_id}/tables`

Назначение: список столов филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
search
zone
is_active
limit
offset
page
sort_by
sort_order
```

#### `POST /api/v1/crm/branches/{branch_id}/tables`

Назначение: создать стол и QR.

Request:

```json
{
  "title": "A-5",
  "number": "A-5",
  "zone": "Главный зал",
  "seats": 4,
  "is_active": true
}
```

Response must include:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "id": 1,
    "title": "A-5",
    "number": "A-5",
    "zone": "Главный зал",
    "seats": 4,
    "qr_token": "token",
    "public_url": "https://qmenu.kg/guest/table/token",
    "is_active": true
  }
}
```

Почему `public_url` обязателен:

- CRM должна копировать готовую ссылку;
- frontend не должен собирать QR URL вручную.

#### `GET /api/v1/crm/branches/{branch_id}/tables/{table_id}`

Назначение: деталка стола.

#### `PATCH /api/v1/crm/branches/{branch_id}/tables/{table_id}`

Request:

```json
{
  "title": "A-5",
  "number": "A-5",
  "zone": "Главный зал",
  "seats": 4,
  "is_active": true
}
```

#### `DELETE /api/v1/crm/branches/{branch_id}/tables/{table_id}`

Назначение: удалить/деактивировать стол.

Если по столу есть активная сессия, backend должен вернуть пользовательскую ошибку.

### 8.7 Employees

#### `GET /api/v1/crm/users/search`

Назначение: поиск пользователей при добавлении сотрудника.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`, если ему разрешено добавлять сотрудников.

Filters:

```txt
search
role
is_active
limit
offset
page
```

Почему нужно:

- пользователь не должен знать `user_id`;
- CRM форма должна иметь searchable select.

#### `GET /api/v1/crm/branches/{branch_id}/employees`

Назначение: сотрудники филиала.

Filters:

```txt
search
role
status
limit
offset
page
```

#### `POST /api/v1/crm/branches/{branch_id}/employees`

Назначение: назначить пользователя сотрудником филиала.

Request:

```json
{
  "user_id": 15,
  "role": "branch_admin"
}
```

Rules:

- `super_admin` может назначать любые роли кроме ограничений бизнес-логики;
- `owner` может назначать `branch_admin` и `kitchen` в своей компании;
- `branch_admin` не может назначать `owner` или `super_admin`;
- один пользователь не должен дублироваться в одном филиале с той же ролью.

#### `PATCH /api/v1/crm/branches/{branch_id}/employees/{employee_id}`

Request:

```json
{
  "role": "kitchen",
  "status": "active"
}
```

#### `DELETE /api/v1/crm/branches/{branch_id}/employees/{employee_id}`

Назначение: убрать сотрудника из филиала.

#### `GET /api/v1/crm/employees/{employee_id}`

Назначение: деталка назначения сотрудника.

Роли:

- `super_admin`;
- `owner` в своей компании;
- `branch_admin` в своем филиале, если имеет доступ к сотрудникам.

Response:

```ts
ApiResponse<Employee>
```

### 8.8 CRM Orders

#### `GET /api/v1/crm/branches/{branch_id}/orders`

Назначение: история/список заказов филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
search
table_id
participant_id
status
moderation_status
created_at_from
created_at_to
limit
offset
page
sort_by
sort_order
```

#### `GET /api/v1/crm/branches/{branch_id}/orders/moderation`

Назначение: очередь заказов, которые ждут подтверждения.

Filters:

```txt
table_id
created_at_from
created_at_to
limit
offset
page
```

#### `GET /api/v1/crm/orders/{order_id}`

Назначение: деталка заказа.

Response:

```ts
ApiResponse<Order>
```

#### `POST /api/v1/crm/branches/{branch_id}/orders/{order_id}/approve`

Назначение: подтвердить заказ.

Rules:

- доступ только к заказам своего branch scope;
- после approve заказ идет в KDS.

#### `POST /api/v1/crm/branches/{branch_id}/orders/{order_id}/reject`

Назначение: отклонить заказ.

Request:

```json
{
  "reason": "Позиция недоступна"
}
```

Поля:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `reason` | string | yes | guest должен увидеть понятную причину |

#### `POST /api/v1/crm/branches/{branch_id}/orders/{order_id}/cancel`

Назначение: отменить заказ администратором филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Request:

```json
{
  "reason": "Гость отменил заказ"
}
```

Rules:

- backend должен проверить, что заказ принадлежит branch;
- если заказ уже `served`, отменять нельзя;
- причина отмены должна быть видна в деталке заказа.

#### `POST /api/v1/crm/branches/{branch_id}/orders/{order_id}/served`

Назначение: отметить заказ выданным со стороны CRM.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Почему нужно:

- mobile сейчас не рассматриваем;
- если KDS только готовит, CRM должна иметь способ закрыть заказ как выданный;
- можно использовать этот endpoint вместо KDS `served`, если решим, что кухня не отмечает выдачу.

### 8.9 CRM Sessions

#### `GET /api/v1/crm/branches/{branch_id}/sessions`

Назначение: активные и завершенные сессии столов филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Filters:

```txt
status
table_id
opened_at_from
opened_at_to
limit
offset
page
```

Почему нужно:

- branch_admin может понять, какие столы сейчас активны;
- owner может проверить текущую операционку филиала.

#### `GET /api/v1/crm/sessions/{session_id}`

Назначение: деталка сессии, участники, заказы.

#### `POST /api/v1/crm/sessions/{session_id}/close`

Назначение: закрыть сессию стола администратором.

#### `GET /api/v1/crm/sessions/{session_id}/participants`

Назначение: участники сессии для CRM.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Response:

```ts
Participant[]
```

#### `POST /api/v1/crm/sessions/{session_id}/participants/{participant_id}/decide`

Назначение: подтвердить или отклонить участника со стороны CRM.

Request:

```json
{
  "decision": "approved"
}
```

Почему нужно:

- если host не подтверждает участника, branch_admin может решить вопрос через CRM;
- это закрывает web-only flow без mobile.

### 8.10 CRM Users

Эти endpoint нужны для базового управления пользователями, которых потом можно назначать как owner, branch_admin или kitchen.

#### `GET /api/v1/crm/users`

Назначение: список пользователей системы.

Роли:

- `super_admin`;
- `owner` в рамках своей компании, если нужно видеть сотрудников компании.

Filters:

```txt
search
role
is_active
company_id
branch_id
limit
offset
page
sort_by
sort_order
```

Response:

```ts
PaginationResponse<User>
```

Почему нужно:

- `super_admin` должен находить пользователей и назначать владельцев;
- owner может видеть пользователей, связанных со своей компанией;
- это полезно для администрирования доступов.

#### `POST /api/v1/crm/users`

Назначение: создать пользователя для дальнейшего назначения роли.

Роли:

- `super_admin`;
- `owner`, если ему разрешено создавать сотрудников своей компании.

Request:

```json
{
  "login": "branch-admin",
  "password": "temporary-password",
  "full_name": "Администратор филиала",
  "phone": "+996700000000",
  "is_active": true
}
```

Поля:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `login` | string | yes | пользователь будет входить в CRM/KDS |
| `password` | string | yes | временный пароль |
| `full_name` | string | yes | отображение в CRM |
| `phone` | string | no | контакт и поиск |
| `is_active` | boolean | yes | можно сразу отключить доступ |

Почему нужно:

- не всегда пользователь уже существует;
- owner/super_admin должен иметь понятный flow: создать пользователя -> назначить сотрудником.

#### `GET /api/v1/crm/users/{user_id}`

Назначение: деталка пользователя.

Роли:

- `super_admin`;
- `owner` для пользователя своей компании.

Response:

```ts
ApiResponse<User>
```

#### `PATCH /api/v1/crm/users/{user_id}`

Назначение: обновить базовые данные пользователя.

Request:

```json
{
  "full_name": "Новое имя",
  "phone": "+996700000000",
  "is_active": true
}
```

#### `POST /api/v1/crm/users/{user_id}/reset-password`

Назначение: задать новый временный пароль пользователю.

Роли:

- `super_admin`;
- `owner` для сотрудника своей компании, если разрешено.

Request:

```json
{
  "password": "new-temporary-password"
}
```

### 8.11 Company Employees

Эти endpoint нужны для ролей уровня компании, прежде всего owner. Branch employees покрывают филиальные роли, но owner относится к компании.

#### `GET /api/v1/crm/companies/{company_id}/employees`

Назначение: сотрудники компании на уровне компании и всех филиалов.

Роли:

- `super_admin`;
- `owner` своей компании.

Filters:

```txt
search
role
status
branch_id
limit
offset
page
```

Response:

```ts
PaginationResponse<Employee>
```

#### `POST /api/v1/crm/companies/{company_id}/employees`

Назначение: назначить пользователя на роль уровня компании.

Роли:

- `super_admin`;
- `owner`, если назначает допустимую роль внутри своей компании.

Request:

```json
{
  "user_id": 12,
  "role": "owner"
}
```

Правила:

- `super_admin` может назначить owner компании;
- owner не может назначить другого owner без отдельного разрешения;
- `branch_admin` назначается через branch employees.

#### `DELETE /api/v1/crm/companies/{company_id}/employees/{employee_id}`

Назначение: снять пользователя с роли уровня компании.

### 8.12 Branch Settings

Настройки филиала можно редактировать через `PATCH /branches/{branch_id}`, но для frontend удобнее иметь отдельный понятный settings endpoint.

#### `GET /api/v1/crm/branches/{branch_id}/settings`

Назначение: настройки филиала, влияющие на guest/order flow.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Response:

```ts
BranchSettings {
  branch_id: number
  moderation_mode: 'strict' | 'auto'
  allow_guest_join_without_host: boolean
  allow_order_without_approval: boolean
  is_active: boolean
  is_published: boolean
}
```

Поля:

| Поле | Формат | Зачем |
| --- | --- | --- |
| `moderation_mode` | enum | заказ сразу идет на кухню или ждет подтверждения |
| `allow_guest_join_without_host` | boolean | можно ли гостям сразу становиться approved |
| `allow_order_without_approval` | boolean | можно ли pending-гостю отправлять заказ |
| `is_active` | boolean | работает ли филиал в системе |
| `is_published` | boolean | виден ли филиал гостям |

#### `PATCH /api/v1/crm/branches/{branch_id}/settings`

Назначение: обновить настройки филиала.

Request:

```json
{
  "moderation_mode": "strict",
  "allow_guest_join_without_host": false,
  "allow_order_without_approval": false,
  "is_active": true,
  "is_published": true
}
```

### 8.13 Menu Ordering

Порядок категорий и блюд важен для guest menu. Менять порядок через отдельные endpoint удобнее, чем отправлять много PATCH по одному элементу.

#### `POST /api/v1/crm/branches/{branch_id}/menu/categories/reorder`

Назначение: изменить порядок категорий.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Request:

```json
{
  "category_ids": [3, 1, 2]
}
```

Rules:

- все `category_ids` должны принадлежать этому `branch_id`;
- backend обновляет `sort_order` по порядку массива.

#### `POST /api/v1/crm/branches/{branch_id}/menu/items/reorder`

Назначение: изменить порядок блюд внутри категории.

Request:

```json
{
  "category_id": 1,
  "item_ids": [102, 101, 103]
}
```

Rules:

- все `item_ids` должны принадлежать указанной категории и филиалу;
- backend обновляет `sort_order`.

### 8.14 Menu Copy

Для сети с несколькими филиалами важно быстро скопировать меню из одного филиала в другой. Это особенно актуально для `owner`, потому что в MVP заведений и филиалов может быть несколько.

#### `POST /api/v1/crm/branches/{branch_id}/menu/copy-from`

Назначение: скопировать категории и блюда из другого филиала в текущий.

Роли:

- `super_admin`;
- `owner`.

Request:

```json
{
  "source_branch_id": 11,
  "copy_categories": true,
  "copy_items": true,
  "replace_existing": false
}
```

Поля:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `source_branch_id` | number | yes | из какого филиала копировать меню |
| `copy_categories` | boolean | yes | копировать категории |
| `copy_items` | boolean | yes | копировать блюда |
| `replace_existing` | boolean | yes | заменить текущее меню или добавить поверх |

Rules:

- source и target должны быть доступны текущему пользователю;
- картинки можно переиспользовать по URL после копирования;
- backend должен сохранить новый `branch_id` у скопированных категорий и блюд.

### 8.15 Table QR Actions

#### `POST /api/v1/crm/branches/{branch_id}/tables/{table_id}/regenerate-qr`

Назначение: перевыпустить QR токен стола.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Response:

```json
{
  "success": true,
  "message": "QR обновлен",
  "data": {
    "qr_token": "new-token",
    "public_url": "https://qmenu.kg/guest/table/new-token"
  }
}
```

Почему нужно:

- если QR скомпрометирован или стол перенастроили, нужен новый токен;
- frontend не должен генерировать token сам.

#### `GET /api/v1/crm/branches/{branch_id}/tables/{table_id}/qr`

Назначение: получить QR-данные для печати.

Response:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "table_title": "A-5",
    "public_url": "https://qmenu.kg/guest/table/token",
    "qr_token": "token"
  }
}
```

Backend может вернуть только данные, а frontend сам нарисует QR. Генерация PDF может быть отдельной задачей позже.

#### `POST /api/v1/crm/branches/{branch_id}/tables/bulk`

Назначение: создать сразу несколько столов и QR.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Request:

```json
{
  "zone": "Главный зал",
  "prefix": "A",
  "from": 1,
  "to": 10,
  "seats": 4
}
```

Response:

```ts
ApiResponse<Table[]>
```

Почему нужно:

- ресторан редко создает только один стол;
- для запуска филиала удобнее создать 10-30 QR за одно действие;
- backend должен гарантировать уникальность номеров внутри филиала.

### 8.16 CRM Dashboard Summary

Главную страницу CRM мы сейчас убрали как обязательный UI, но backend может дать компактные summary endpoint-ы для будущих счетчиков в sidebar/detail pages.

#### `GET /api/v1/crm/branches/{branch_id}/summary`

Назначение: краткая сводка филиала.

Роли:

- `super_admin`;
- `owner`;
- `branch_admin`.

Response:

```ts
BranchSummary {
  active_sessions_count: number
  pending_orders_count: number
  cooking_orders_count: number
  ready_orders_count: number
  unavailable_items_count: number
  tables_count: number
}
```

Почему это полезно:

- можно показывать счетчики на деталке филиала;
- не нужно тянуть все заказы/столы/меню ради маленьких чисел.

## 9. Guest Public API

Guest endpoint не требуют CRM `Authorization`.

Для table session requests используется `X-Participant-Token`.

### `GET /api/v1/public/restaurant-types`

Назначение: фильтры типов заведений на guest-главной.

Response:

```ts
RestaurantType[]
```

### `GET /api/v1/public/places`

Назначение: публичный список заведений.

Filters:

```txt
search
type_ids
city
limit
offset
page
```

Response:

```ts
PaginationResponse<PublicPlaceListItem>
```

```ts
PublicPlaceListItem {
  id: number
  slug: string
  title: string
  short_description: string
  type_ids: string[]
  type_title: string
  logo_url: string
  cover_url: string
  branches_count: number
}
```

Поля:

| Поле | Зачем |
| --- | --- |
| `slug` | открыть деталку заведения |
| `title` | название карточки |
| `short_description` | описание в карточке |
| `type_title` | badge типа заведения |
| `logo_url` | маленькая картинка/логотип |
| `cover_url` | большая картинка карточки |
| `branches_count` | показать масштаб заведения |

Rules:

- отдавать только `is_active=true`;
- отдавать только `is_published=true`;
- не отдавать CRM/private поля.

### `GET /api/v1/public/places/{place_slug}`

Назначение: публичная деталка заведения.

Response:

```ts
PublicPlaceDetails {
  id: number
  slug: string
  title: string
  description: string
  type_ids: string[]
  type_title: string
  logo_url: string
  cover_url: string
  branches: PublicBranchListItem[]
}
```

```ts
PublicBranchListItem {
  id: number
  slug: string
  title: string
  address: string
  city: string
  cover_url: string
  working_hours: string
  is_open: boolean
}
```

### `GET /api/v1/public/places/{place_slug}/branches`

Назначение: публичный список филиалов заведения отдельным endpoint.

Filters:

```txt
city
is_open
limit
offset
page
```

Response:

```ts
PaginationResponse<PublicBranchListItem>
```

Почему нужно:

- если филиалов много, не нужно отдавать их все в деталке заведения;
- можно отдельно пагинировать и фильтровать филиалы.

Для первого этапа можно также отдавать филиалы внутри `GET /public/places/{place_slug}`, но контракт отдельного endpoint стоит зафиксировать.

### `GET /api/v1/public/branches/{branch_slug}`

Назначение: публичная деталка филиала без меню.

Response:

```ts
PublicBranchDetails {
  id: number
  slug: string
  title: string
  address: string
  city: string
  cover_url: string
  working_hours: string
  is_open: boolean
  place: PublicPlaceSummary
}
```

Почему нужно:

- frontend может открыть филиал напрямую;
- если ссылка ведет сразу на branch, не нужно сначала загружать place.

### `GET /api/v1/public/places/{place_slug}/branches/{branch_slug}/menu`

Назначение: preview-меню филиала до QR.

Response:

```ts
PublicBranchMenu {
  place: PublicPlaceSummary
  branch: PublicBranchDetails
  categories: PublicMenuCategory[]
}
```

```ts
PublicMenuCategory {
  id: number
  slug: string
  title: string
  sort_order: number
  items: PublicMenuItem[]
}
```

```ts
PublicMenuItem {
  id: number
  title: string
  description: string
  image_url: string
  price: number
  weight?: number
  weight_unit?: 'g' | 'ml' | 'pcs'
  is_available: boolean
}
```

Rules:

- preview-меню только для просмотра;
- отдавать только опубликованные категории;
- отдавать только опубликованные блюда;
- если блюдо в stop-list, можно показать `is_available=false`.

### `GET /api/v1/public/branches/{branch_slug}/menu`

Назначение: альтернативный короткий endpoint для preview-меню филиала.

Response:

```ts
PublicBranchMenu
```

Почему нужен:

- в QR/public links иногда удобнее знать только `branch_slug`;
- endpoint проще для frontend, если place уже не нужен в path.

### `GET /api/v1/public/branches/{branch_slug}/menu/items/{item_id}`

Назначение: публичная деталка блюда в preview mode.

Response:

```ts
ApiResponse<PublicMenuItemDetails>
```

```ts
PublicMenuItemDetails {
  id: number
  title: string
  description: string
  image_url: string
  price: number
  weight?: number
  weight_unit?: 'g' | 'ml' | 'pcs'
  is_available: boolean
  category: {
    id: number
    title: string
  }
}
```

Можно не делать отдельную страницу блюда на первом frontend-этапе, но endpoint полезен для модалки блюда.

### `GET /api/v1/public/branches/{branch_slug}/menu/search`

Назначение: поиск блюд внутри preview-меню филиала.

Filters:

```txt
search
category_id
is_available
limit
offset
page
```

Response:

```ts
PaginationResponse<PublicMenuItem>
```

Почему нужно:

- если меню большое, frontend не должен загружать все блюда и фильтровать их локально;
- поиск должен работать быстро и одинаково на всех устройствах.

### `POST /api/v1/public/tables/scan`

Назначение: открыть или присоединиться к table session после QR.

Request:

```json
{
  "qr_token": "table-token",
  "participant_name": "Гость"
}
```

Поля:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `qr_token` | string | yes | найти стол |
| `participant_name` | string | yes | отобразить гостя в участниках |

Response:

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "session": {},
    "participant": {},
    "participant_token": "token-for-current-guest",
    "mode": "host"
  }
}
```

Rules:

- если активной сессии стола нет, создать ее;
- первый гость становится `host`;
- если сессия уже есть, гость становится `pending` или `approved` по настройке филиала;
- вернуть `participant_token`, чтобы guest мог делать дальнейшие requests.

### `GET /api/v1/public/tables/{qr_token}`

Назначение: получить публичную информацию о столе до создания/присоединения к session.

Response:

```ts
PublicTablePreview {
  qr_token: string
  table_title: string
  table_zone: string
  branch: PublicBranchDetails
  place: PublicPlaceSummary
}
```

Почему нужно:

- frontend может показать экран подтверждения после QR;
- если QR невалидный, можно показать красивую ошибку.

### `GET /api/v1/public/sessions/{session_id}/state`

Назначение: получить текущее состояние стола.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Response:

```ts
{
  session: TableSession
  place: PublicPlaceSummary
  branch: PublicBranchDetails
  table: Table
  participant: Participant
  participants: Participant[]
  categories: PublicMenuCategory[]
  orders: Order[]
}
```

Почему response должен быть широким:

- Guest page может отрендерить меню, стол, участников и заказы одним запросом;
- меньше состояния нужно собирать на frontend.

### `GET /api/v1/public/sessions/{session_id}/menu`

Назначение: получить меню внутри активной table session.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Response:

```ts
PublicBranchMenu
```

Почему отдельный endpoint полезен:

- state можно обновлять часто, а меню редко;
- если меню большое, не нужно каждый раз тянуть его вместе с участниками и заказами.

### `GET /api/v1/public/sessions/{session_id}/participants`

Назначение: участники текущего стола.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Response:

```ts
Participant[]
```

### `POST /api/v1/public/sessions/{session_id}/participants/{participant_id}/decide`

Назначение: host подтверждает или отклоняет участника.

Headers:

```txt
X-Participant-Token: <host_participant_token>
```

Request:

```json
{
  "decision": "approved"
}
```

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `decision` | `approved` или `rejected` | yes | решение host |

### `PATCH /api/v1/public/sessions/{session_id}/participants/me`

Назначение: изменить имя текущего гостя.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Request:

```json
{
  "name": "Даурен"
}
```

Почему нужно:

- guest может сначала войти как `Гость`, а потом указать имя;
- имя отображается в участниках и заказах.

### `POST /api/v1/public/sessions/{session_id}/participants/me/leave`

Назначение: выйти из сессии стола.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Rules:

- если выходит обычный participant, он становится inactive/left;
- если выходит host, backend должен либо запретить выход, либо передать host другому участнику. Для базового этапа проще запретить и вернуть понятную ошибку.

### `POST /api/v1/public/sessions/{session_id}/orders`

Назначение: создать заказ из frontend-корзины.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Request:

```json
{
  "comment": "Без лука",
  "items": [
    {
      "menu_item_id": 401,
      "quantity": 2,
      "comment": "Острое отдельно"
    }
  ]
}
```

Fields:

| Поле | Формат | Required | Зачем |
| --- | --- | --- | --- |
| `comment` | string | no | общий комментарий к заказу |
| `items` | array | yes | позиции заказа |
| `items.menu_item_id` | number | yes | какое блюдо заказали |
| `items.quantity` | number | yes | количество |
| `items.comment` | string | no | комментарий к позиции |

Backend rules:

- проверить, что session open;
- проверить, что participant имеет право заказывать;
- проверить, что блюда принадлежат branch этой session;
- проверить, что блюда опубликованы и доступны;
- сохранить snapshot названия и цены;
- посчитать total на backend;
- создать order.

### `GET /api/v1/public/sessions/{session_id}/orders`

Назначение: заказы текущей сессии.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Rules:

- host может видеть все заказы стола;
- обычный участник минимум должен видеть свои заказы;
- backend должен не отдавать заказы чужой сессии.

### `GET /api/v1/public/sessions/{session_id}/orders/{order_id}`

Назначение: деталка заказа внутри guest session.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Response:

```ts
ApiResponse<Order>
```

Rules:

- host может открыть любой заказ текущей сессии;
- participant может открыть свой заказ;
- нельзя открыть заказ другой сессии.

### `POST /api/v1/public/sessions/{session_id}/orders/{order_id}/cancel`

Назначение: отменить заказ гостем, если он еще не ушел на кухню.

Headers:

```txt
X-Participant-Token: <participant_token>
```

Request:

```json
{
  "reason": "Передумали"
}
```

Rules:

- можно отменять только свои заказы;
- host может отменить заказ стола, если это разрешено;
- нельзя отменить заказ после `cooking`, если backend запрещает.

### `POST /api/v1/public/sessions/{session_id}/close`

Назначение: закрыть сессию host-ом, если такой flow разрешен.

Headers:

```txt
X-Participant-Token: <host_participant_token>
```

Можно не делать на самом первом этапе, если сессию закрывает только CRM.

## 10. KDS API

Все KDS endpoint требуют:

```txt
Authorization: Bearer <access_token>
```

Роль:

- `kitchen`.

### `GET /api/v1/kds/branches/my`

Назначение: список филиалов, доступных кухне.

Response:

```ts
Branch[]
```

### `GET /api/v1/kds/branches/{branch_id}/orders`

Назначение: доска заказов кухни.

Filters:

```txt
status
cooking_zone
created_at_from
created_at_to
limit
offset
page
```

Response:

```ts
PaginationResponse<KdsOrder>
```

```ts
KdsOrder {
  id: number
  table_title: string
  table_zone: string
  status: string
  created_at: string
  items: KdsOrderItem[]
}
```

```ts
KdsOrderItem {
  id: number
  title_snapshot: string
  quantity: number
  comment?: string
  status: string
}
```

Почему KDS response отличается от CRM:

- кухня не должна получать лишние CRM-поля;
- кухне нужны стол, зона, позиции, комментарии и статус.

### `GET /api/v1/kds/branches/{branch_id}/orders/{order_id}`

Назначение: деталка заказа для KDS.

Роли:

- `kitchen`.

Response:

```ts
ApiResponse<KdsOrder>
```

Почему нужно:

- KDS может открыть заказ отдельно;
- polling списка и деталка заказа могут жить раздельно;
- кухня не должна получать CRM-поля.

### `POST /api/v1/kds/branches/{branch_id}/orders/{order_id}/cooking`

Назначение: взять заказ в работу.

### `POST /api/v1/kds/branches/{branch_id}/orders/{order_id}/ready`

Назначение: отметить заказ готовым.

### `POST /api/v1/kds/branches/{branch_id}/orders/{order_id}/served`

Назначение: отметить заказ выданным.

На базовом этапе статусы можно менять на уровне заказа. Позже можно перейти на item-level.

## 11. Минимальный backend checklist

Чтобы показать полный базовый web-flow, backend должен закрыть:

### Auth

- `POST /auth/login`;
- `GET /auth/me`;
- `POST /auth/refresh`;
- `POST /auth/logout`;
- role/scopes/permissions в `me`.

### CRM

- компании с описанием, типами, logo, cover;
- филиалы с address, city, schedule, cover, moderation mode;
- типы заведений;
- категории меню;
- изменение порядка категорий;
- блюда с image, description, price, weight, availability;
- изменение порядка блюд;
- быстрое изменение доступности блюда;
- столы с `public_url`;
- получение QR-данных стола;
- перевыпуск QR стола;
- настройки филиала;
- поиск пользователей;
- сотрудники и назначение ролей;
- сотрудники уровня компании;
- сотрудники уровня филиала;
- список заказов филиала;
- очередь модерации;
- активные сессии столов;
- деталка сессии;
- закрытие сессии администратором;
- summary филиала для счетчиков.

### Guest

- публичные типы заведений;
- публичный список заведений;
- публичная деталка заведения;
- публичный список филиалов заведения;
- публичная деталка филиала;
- preview-меню филиала;
- поиск блюд внутри меню;
- деталка блюда;
- публичная информация о столе по QR token;
- скан QR;
- state сессии стола;
- меню внутри table session;
- участники;
- подтверждение/отклонение участника host-ом;
- изменение имени текущего участника;
- выход участника из сессии;
- создание заказа;
- список заказов сессии;
- деталка заказа;
- отмена заказа до кухни.

### KDS

- список доступных филиалов;
- KDS board;
- статусы `cooking`, `ready`, `served`.

### Common

- пагинация на всех списках;
- фильтры на всех списках;
- user-friendly errors;
- `field_errors` для форм;
- картинки через `multipart/form-data`;
- backend permission checks на каждом protected endpoint.

## 12. Главные продуктовые правила

1. Guest может смотреть заведения и preview-меню без QR.
2. Guest может заказывать только после QR.
3. Корзина живет на frontend и становится заказом только после submit.
4. Компания и филиал должны иметь данные для красивой guest-витрины.
5. Меню принадлежит филиалу, а не только компании.
6. Категории обязательны для меню.
7. Блюдо должно иметь фото, описание, цену, доступность и категорию.
8. Backend должен возвращать `public_url` для стола.
9. Backend должен возвращать роль и scopes в `me`.
10. Backend, а не frontend, отвечает за проверку доступа.
11. Все списки должны иметь пагинацию.
12. Все основные списки должны иметь фильтры.
13. Ошибки должны быть понятными пользователю.
14. Ошибки формы должны приходить под конкретные поля.
15. Картинки отправляются файлами через `multipart/form-data`.
