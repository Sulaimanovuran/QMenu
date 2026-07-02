# QMenu Backend — деплой на VPS

Цель: поднять backend на VPS (Ubuntu/Debian) с PostgreSQL так, чтобы
**данные и загруженные картинки переживали передеплой**, и фронтенд мог
протестировать полный клиентский путь. Без S3 и Docker — venv + systemd + nginx.

Сценарий: **домена пока нет**, API доступен по IP VPS (`http://<IP-VPS>`),
фронтенд разработчик запускает у себя локально (`http://localhost:3000`)
и ходит на VPS. Когда появится домен — поменять три переменные в `.env`
(см. таблицу в разделе 3) и выпустить сертификат.

---

## 0. Почему данные не потеряются

- **БД — PostgreSQL.** Схема создаётся автоматически при первом старте
  (`generate_schemas=True` работает в режиме *safe*: создаёт только
  отсутствующие таблицы и **никогда не удаляет** существующие данные).
  Пересоздавать базу, как на dev-SQLite, не нужно.
  ⚠️ Ограничение: если в моделях появятся *новые колонки* в уже существующих
  таблицах, safe-режим их не добавит — потребуется ручной `ALTER TABLE` или
  подключение Aerich-миграций (запланировано этапом 3). Новые таблицы
  подхватываются автоматически.
- **Картинки — в `UPLOAD_DIR` вне репозитория** (`/var/lib/qmenu/uploads`).
  Деплой обновляет код в `/opt/qmenu`, каталог картинок не трогается.
- **Сиды идемпотентны**: роли, типы заведений и пользователь `admin`
  создаются только если их нет — рестарты и передеплои ничего не затирают.

## 1. Подготовка сервера

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql nginx

# системный пользователь без shell
sudo useradd --system --home /opt/qmenu --shell /usr/sbin/nologin qmenu

# каталоги
sudo mkdir -p /opt/qmenu /var/lib/qmenu/uploads
sudo chown -R qmenu:qmenu /opt/qmenu /var/lib/qmenu
```

## 2. PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE USER qmenu WITH PASSWORD 'СМЕНИТЕ_ПАРОЛЬ';
CREATE DATABASE qmenu OWNER qmenu;
SQL
```

Проверка: `psql "postgres://qmenu:ПАРОЛЬ@127.0.0.1:5432/qmenu" -c "select 1;"`

## 3. Код и окружение

```bash
# доставить код (git clone / rsync) в /opt/qmenu
sudo -u qmenu git clone <repo-url> /opt/qmenu   # или rsync -a --exclude venv ...

cd /opt/qmenu
sudo -u qmenu python3.12 -m venv venv
sudo -u qmenu venv/bin/pip install -r req.txt
```

Создать `/opt/qmenu/.env` по образцу `.env.example` — значения для сценария
«API по IP, фронт с локалки» (замените `<IP-VPS>` на реальный адрес):

```env
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
DB_URL=asyncpg://qmenu:СМЕНИТЕ_ПАРОЛЬ@127.0.0.1:5432/qmenu

# guest-фронт крутится у разработчика локально — QR-ссылки ведут туда
PUBLIC_BASE_URL=http://localhost:3000

# фронт подключается с локалки
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

UPLOAD_DIR=/var/lib/qmenu/uploads

# ВАЖНО: фронт на другом origin, относительный /uploads/... у него не откроется.
# Абсолютный префикс = адрес API (nginx на 80 порту)
MEDIA_BASE_URL=http://<IP-VPS>
```

```bash
sudo chown qmenu:qmenu /opt/qmenu/.env && sudo chmod 600 /opt/qmenu/.env
```

Ключевые переменные (и что поменять, когда появится домен):

| Переменная | Сейчас (по IP) | Потом (с доменом) |
| --- | --- | --- |
| `SECRET_KEY` | случайный, уникальный | без изменений |
| `DB_URL` | `asyncpg://user:pass@127.0.0.1:5432/qmenu` | без изменений |
| `PUBLIC_BASE_URL` | `http://localhost:3000` (локальный guest-фронт; из него собирается `public_url` столов) | `https://qmenu.kg` |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | домены фронта |
| `UPLOAD_DIR` | `/var/lib/qmenu/uploads` | без изменений |
| `MEDIA_BASE_URL` | `http://<IP-VPS>` — чтобы `image_url` были абсолютными | `https://api.qmenu.kg` или пусто, если фронт и API на одном домене |

После смены `.env` — `sudo systemctl restart qmenu`.

## 4. systemd

```bash
sudo cp deploy/qmenu.service /etc/systemd/system/qmenu.service
sudo systemctl daemon-reload
sudo systemctl enable --now qmenu
systemctl status qmenu          # должно быть active (running)
journalctl -u qmenu -f          # логи
```

Первый старт создаст таблицы в PostgreSQL и сиды (`admin/admin` — супер-админ;
**сразу смените пароль** через `POST /api/v1/crm/users/{id}/reset-password`).

## 5. nginx (reverse proxy + раздача картинок)

`/etc/nginx/sites-available/qmenu-api`:

```nginx
server {
    listen 80 default_server;
    server_name _;                          # домена нет — отвечаем по IP

    client_max_body_size 10m;               # запас под загрузку картинок

    # загруженные картинки — напрямую с диска, мимо приложения
    location /uploads/ {
        alias /var/lib/qmenu/uploads/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/qmenu-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Проверка: `curl http://<IP-VPS>/health` → `{"status":"ok"}`,
Swagger — `http://<IP-VPS>/docs`.

Когда появится домен: вписать `server_name api.qmenu.kg;` и выпустить
сертификат `sudo certbot --nginx -d api.qmenu.kg`.

## 6. Обновление кода (передеплой)

```bash
cd /opt/qmenu
sudo -u qmenu git pull
sudo -u qmenu venv/bin/pip install -r req.txt
sudo systemctl restart qmenu
```

БД и `/var/lib/qmenu/uploads` не затрагиваются. Если релиз добавил **новые
колонки в существующие таблицы** — примените `ALTER TABLE` из changelog релиза
до рестарта (до подключения Aerich).

## 7. Smoke-тест клиентского пути

После деплоя прогнать руками весь guest-путь (подставьте IP вашего VPS):

```bash
API=http://<IP-VPS>/api/v1

# 1) health + справочники
curl -s $API/../health
curl -s $API/public/restaurant-types | head -c 200

# 2) логин супер-админа
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"login":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')
AUTH="Authorization: Bearer $TOKEN"

# 3) компания + филиал + меню + стол
CID=$(curl -s -X POST $API/crm/companies/ -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Тестовое кафе","type_codes":["coffee"],"is_published":true,"status":"active"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')
BID=$(curl -s -X POST $API/crm/companies/$CID/branches -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Центр","city":"Бишкек","address":"Чуй 1","moderation_mode":"strict","is_published":true,"status":"active"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')
CAT=$(curl -s -X POST $API/crm/branches/$BID/categories -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Напитки","sort_order":0,"is_published":true}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')
ITEM=$(curl -s -X POST $API/crm/branches/$BID/items -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"category_id\":$CAT,\"title\":\"Чай\",\"price_minor\":10000,\"sort_order\":0,\"is_published\":true}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')
QR=$(curl -s -X POST $API/crm/branches/$BID/tables -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"number":"A1","zone":"Зал"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["qr_token"])')

# 4) загрузка картинки (проверка UPLOAD_DIR и nginx /uploads/)
curl -s -X POST $API/crm/uploads -H "$AUTH" -F "file=@/path/to/photo.jpg"
# image_url в ответе будет абсолютным (http://<IP-VPS>/uploads/...) —
# открыть его в браузере, картинка должна отдаться

# 5) гостевой путь: скан -> заказ
SCAN=$(curl -s -X POST $API/public/sessions/scan -H 'Content-Type: application/json' \
  -d "{\"qr_token\":\"$QR\",\"display_name\":\"Гость\"}")
DT=$(echo $SCAN | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["device_token"])')
SID=$(echo $SCAN | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["session"]["id"])')
OID=$(curl -s -X POST $API/public/sessions/$SID/orders -H "X-Device-Token: $DT" \
  -H 'Content-Type: application/json' \
  -d "{\"device_token\":\"$DT\",\"items\":[{\"menu_item_id\":$ITEM,\"qty\":2}]}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')

# 6) модерация -> кухня -> выдача
curl -s -X POST $API/crm/branches/$BID/orders/$OID/approve -H "$AUTH" | head -c 120
curl -s -X POST $API/kds/branches/$BID/orders/$OID/cooking -H "$AUTH" | head -c 120
curl -s -X POST $API/kds/branches/$BID/orders/$OID/ready   -H "$AUTH" | head -c 120
curl -s -X POST $API/crm/branches/$BID/orders/$OID/served  -H "$AUTH" | head -c 120

# 7) публичная витрина
curl -s "$API/public/places" | head -c 300
```

Если все шаги вернули `"success": true` — клиентский путь работоспособен,
фронтенд может подключаться.

## 8. Проверка сохранности после рестарта

```bash
sudo systemctl restart qmenu
curl -s $API/public/places | head -c 300     # компания на месте
# картинка по своему /uploads/... URL по-прежнему открывается
```

## Чек-лист безопасности перед выдачей доступа фронту

- [ ] `SECRET_KEY` заменён на случайный;
- [ ] пароль `admin` сменён;
- [ ] PostgreSQL слушает только 127.0.0.1 (по умолчанию так);
- [ ] `.env` имеет права 600;
- [ ] `CORS_ORIGINS` содержит только адреса, с которых реально работает фронт;
- [ ] HTTPS через certbot — когда появится домен (по IP сертификат не выдаётся).
