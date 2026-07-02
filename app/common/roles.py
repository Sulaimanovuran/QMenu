"""Фиксированный справочник ролей и сидирование при старте."""
from app.models import Role

# code -> человекочитаемое название. Произвольных прав нет — только этот набор.
# super_admin в этот справочник не входит: это платформенная роль, она не
# назначается через Employee (нет branch/company), а хранится флагом
# User.is_superadmin — см. app/common/security.py.
FIXED_ROLES: dict[str, str] = {
    "owner": "Владелец",
    "branch_admin": "Администратор филиала",
    "waiter": "Официант",
    "kitchen": "Кухня",
}


async def seed_roles() -> None:
    """Создаёт недостающие роли. Идемпотентно (можно звать на каждый старт)."""
    for code, title in FIXED_ROLES.items():
        await Role.get_or_create(code=code, defaults={"title": title})


# Статический набор permission-строк по роли для GET /auth/me (контракт п.6).
# super_admin в FIXED_ROLES не входит (см. выше), но участвует в /auth/me.
PERMISSIONS_BY_ROLE: dict[str, list[str]] = {
    "super_admin": [
        "companies.manage", "branches.manage", "menu.manage",
        "tables.manage", "staff.manage", "orders.manage",
    ],
    "owner": [
        "companies.read", "companies.update", "branches.manage",
        "menu.manage", "tables.manage", "staff.manage", "orders.manage",
    ],
    "branch_admin": [
        "branches.read", "menu.manage", "tables.manage",
        "staff.manage", "orders.manage",
    ],
    # официант: только модерация заказов (approve/reject/served), без меню/
    # столов/сотрудников — по объёму прав меньше branch_admin/owner.
    "waiter": ["orders.read", "orders.moderate"],
    "kitchen": ["orders.read", "orders.kitchen_actions"],
}
