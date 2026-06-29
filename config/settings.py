import os
from decouple import config

SECRET_KEY = config("SECRET_KEY", default="dev-insecure-change-me-0123456789abcdef")

APPS_MODEL = ["app.models"]

DB_URL = config("DB_URL", default="sqlite://db.sqlite3")

PUBLIC_BASE_URL = config("PUBLIC_BASE_URL", default="http://localhost:3000")

CORS_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
