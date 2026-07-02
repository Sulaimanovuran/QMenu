import os
from decouple import config

SECRET_KEY = config("SECRET_KEY", default="dev-insecure-change-me-0123456789abcdef")

APPS_MODEL = ["app.models"]

DB_URL = config("DB_URL", default="sqlite://db.sqlite3")
# Render/Heroku отдают connection string со схемой postgresql:// —
# Tortoise понимает только postgres:// / asyncpg://. Нормализуем прозрачно.
if DB_URL.startswith("postgresql://"):
    DB_URL = "postgres://" + DB_URL[len("postgresql://"):]

PUBLIC_BASE_URL = config("PUBLIC_BASE_URL", default="http://localhost:3000")

ACCESS_TOKEN_TTL_MINUTES = config("ACCESS_TOKEN_TTL_MINUTES", default=30, cast=int)
REFRESH_TOKEN_TTL_DAYS = config("REFRESH_TOKEN_TTL_DAYS", default=30, cast=int)

# Базовый URL для отдачи загруженных картинок. Пусто -> относительный путь
# /uploads/<file>. На проде можно указать CDN/домен API.
MEDIA_BASE_URL = config("MEDIA_BASE_URL", default="")
MAX_UPLOAD_BYTES = config("MAX_UPLOAD_BYTES", default=5 * 1024 * 1024, cast=int)

# CSV-список origin'ов фронтенда: CORS_ORIGINS=https://qmenu.kg,https://admin.qmenu.kg
CORS_ORIGINS = [
    origin.strip()
    for origin in config(
        "CORS_ORIGINS", default="http://127.0.0.1:3000,http://localhost:3000"
    ).split(",")
    if origin.strip()
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# на сервере выносится из репозитория (например /var/lib/qmenu/uploads),
# чтобы деплой/git clean не трогали загруженные картинки
UPLOAD_DIR = config("UPLOAD_DIR", default=os.path.join(BASE_DIR, "uploads"))
