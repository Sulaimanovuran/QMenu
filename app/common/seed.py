"""Стартовое наполнение справочников (идемпотентно)."""
from app.models import RestaurantType

# базовые типы заведений (контракт 7.3)
DEFAULT_RESTAURANT_TYPES: list[tuple[str, str, int]] = [
    ("coffee", "Кофейня", 1),
    ("chaikhana", "Чайхана", 2),
    ("restaurant", "Ресторан", 3),
    ("fastfood", "Фастфуд", 4),
    ("pizza", "Пиццерия", 5),
    ("sushi", "Суши", 6),
]


async def seed_restaurant_types() -> None:
    for code, title, sort_order in DEFAULT_RESTAURANT_TYPES:
        await RestaurantType.get_or_create(
            code=code, defaults={"title": title, "sort_order": sort_order}
        )
