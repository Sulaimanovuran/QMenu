"""Конфиг Tortoise для Aerich (миграции).

Использование:
    aerich init -t config.tortoise_config.TORTOISE_ORM
"""
from config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DB_URL},
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
