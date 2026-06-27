"""Фиксированный справочник ролей и сидирование при старте."""
from app.models import Role

# code -> человекочитаемое название. Произвольных прав нет — только этот набор.
FIXED_ROLES: dict[str, str] = {
    "owner": "Владелец",
    "admin": "Администратор",
    "manager": "Менеджер",
    "senior_waiter": "Старший официант",
    "waiter": "Официант",
    "kitchen": "Кухня",
}


async def seed_roles() -> None:
    """Создаёт недостающие роли. Идемпотентно (можно звать на каждый старт)."""
    for code, title in FIXED_ROLES.items():
        await Role.get_or_create(code=code, defaults={"title": title})
