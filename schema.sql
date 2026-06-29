CREATE TABLE IF NOT EXISTS "role" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "code" VARCHAR(32) NOT NULL UNIQUE,
    "title" VARCHAR(64) NOT NULL
) /* Фиксированные роли сотрудников. */;
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(25) NOT NULL,
    "password_hash" VARCHAR(128) NOT NULL
);
CREATE TABLE IF NOT EXISTS "company" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMP NOT NULL,
    "owner_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
) /* Компания (юрлицо \/ бренд). Владелец — пользователь User. */;
CREATE TABLE IF NOT EXISTS "branch" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(80) NOT NULL,
    "address" VARCHAR(255),
    "moderation_mode" VARCHAR(16) NOT NULL,
    "is_active" INT NOT NULL,
    "created_at" TIMESTAMP NOT NULL,
    "company_id" INT NOT NULL REFERENCES "company" ("id") ON DELETE CASCADE
) /* Филиал \/ заведение. Принадлежит компании. Меню привязано сюда. */;
CREATE TABLE IF NOT EXISTS "employee" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "is_active" INT NOT NULL,
    "created_at" TIMESTAMP NOT NULL,
    "branch_id" INT NOT NULL REFERENCES "branch" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE RESTRICT,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_employee_user_id_13530d" UNIQUE ("user_id", "branch_id")
) /* Сотрудник в конкретном филиале с фиксированной ролью. */;
CREATE TABLE IF NOT EXISTS "menu_category" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(80) NOT NULL,
    "sort_order" INT NOT NULL,
    "is_active" INT NOT NULL,
    "branch_id" INT NOT NULL REFERENCES "branch" ("id") ON DELETE CASCADE
) /* Категория меню филиала (Горячее, Напитки и т.д.). */;
CREATE TABLE IF NOT EXISTS "menu_item" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(120) NOT NULL,
    "description" TEXT,
    "price_minor" INT NOT NULL,
    "photo_url" VARCHAR(255),
    "is_in_stoplist" INT NOT NULL,
    "sort_order" INT NOT NULL,
    "category_id" INT NOT NULL REFERENCES "menu_category" ("id") ON DELETE CASCADE
) /* Блюдо \/ напиток. Цена в минимальных единицах (тыйын) во избежание float. */;
CREATE TABLE IF NOT EXISTS "restaurant_table" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "number" VARCHAR(16) NOT NULL,
    "zone" VARCHAR(40),
    "qr_token" VARCHAR(64) NOT NULL UNIQUE,
    "is_active" INT NOT NULL,
    "branch_id" INT NOT NULL REFERENCES "branch" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_restaurant__branch__a8b6b3" UNIQUE ("branch_id", "number")
) /* Стол в филиале. qr_token зашит в QR-ссылку и публично сканируется. */;
CREATE TABLE IF NOT EXISTS "table_session" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "status" VARCHAR(16) NOT NULL,
    "host_participant_id" INT,
    "opened_at" TIMESTAMP NOT NULL,
    "closed_at" TIMESTAMP,
    "table_id" INT NOT NULL REFERENCES "restaurant_table" ("id") ON DELETE CASCADE
) /* Сессия стола (визит). Один общий чек на стол (гибрид: см. participants). */;
CREATE TABLE IF NOT EXISTS "session_participant" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "device_token" VARCHAR(64) NOT NULL,
    "display_name" VARCHAR(40),
    "status" VARCHAR(16) NOT NULL,
    "joined_at" TIMESTAMP NOT NULL,
    "session_id" INT NOT NULL REFERENCES "table_session" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_session_par_session_b989cb" UNIQUE ("session_id", "device_token")
) /* Участник стола в рамках одной сессии. */;
CREATE TABLE IF NOT EXISTS "order" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "status" VARCHAR(16) NOT NULL,
    "total_minor" INT NOT NULL,
    "comment" TEXT,
    "reject_reason" VARCHAR(255),
    "created_at" TIMESTAMP NOT NULL,
    "updated_at" TIMESTAMP NOT NULL,
    "moderated_by_id" INT REFERENCES "employee" ("id") ON DELETE SET NULL,
    "participant_id" INT NOT NULL REFERENCES "session_participant" ("id") ON DELETE CASCADE,
    "session_id" INT NOT NULL REFERENCES "table_session" ("id") ON DELETE CASCADE
) /* Заказ в рамках сессии стола, сделанный конкретным участником. */;
CREATE TABLE IF NOT EXISTS "order_item" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title_snapshot" VARCHAR(120) NOT NULL,
    "price_minor" INT NOT NULL,
    "qty" INT NOT NULL,
    "comment" VARCHAR(255),
    "menu_item_id" INT NOT NULL REFERENCES "menu_item" ("id") ON DELETE RESTRICT,
    "order_id" INT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE
) /* Позиция заказа. Цена фиксируется на момент заказа (price_minor). */;
