"""Единая точка регистрации ORM-моделей и генерации Pydantic-схем.

Порядок важен: сначала импортируем все модели, затем Tortoise.init_models()
разрешает строковые связи ("models.X"), и только после этого
pydantic_model_creator может корректно построить схемы со связями.
"""
from tortoise import Tortoise

from .roles import Role
from .users import User
from .auth import RefreshToken
from .restaurant_types import RestaurantType
from .companies import Company, Branch
from .staff import Employee
from .menu import MenuCategory, MenuItem
from .tables import Table
from .sessions import TableSession, SessionParticipant
from .orders import Order, OrderItem

# Разрешаем все связи между моделями до создания Pydantic-схем.
Tortoise.init_models(["app.models"], "models")

from tortoise.contrib.pydantic import pydantic_model_creator  # noqa: E402

# ── Pydantic-схемы (вход In / выход Get) ─────────────────────────────────────
# exclude связей: схема ответа не должна тянуть owner целиком (там password_hash)
# и обратные связи (branches/employees) — иначе нужен prefetch на каждый запрос.
GetRestaurantType = pydantic_model_creator(RestaurantType, name="RestaurantType")

GetCompany = pydantic_model_creator(
    Company, name="Company",
    exclude=("owner", "branches", "employees"),
    include=("id", "slug", "title", "description", "short_description",
             "type_codes", "logo_url", "cover_url", "owner_id", "status",
             "is_active", "is_published", "created_at", "updated_at"),
)

GetBranch = pydantic_model_creator(
    Branch, name="Branch",
    exclude=("company", "employees", "categories", "tables"),
    include=("id", "company_id", "slug", "title", "address", "city",
             "latitude", "longitude", "phone", "cover_url", "working_hours",
             "schedule", "moderation_mode", "allow_guest_join_without_host",
             "allow_order_without_approval", "status", "is_active",
             "is_published", "created_at", "updated_at"),
)

GetCategory = pydantic_model_creator(
    MenuCategory, name="MenuCategory", exclude=("branch", "items"),
)
GetMenuItem = pydantic_model_creator(
    MenuItem, name="MenuItem", exclude=("category", "order_items"),
)
GetTable = pydantic_model_creator(
    Table, name="Table", exclude=("branch", "sessions"),
)
GetSession = pydantic_model_creator(
    TableSession, name="TableSession", exclude=("table", "participants", "orders"),
)
GetParticipant = pydantic_model_creator(
    SessionParticipant, name="SessionParticipant", exclude=("session", "orders"),
)
GetOrder = pydantic_model_creator(
    Order, name="Order",
    exclude=("session", "participant", "moderated_by", "items"),
)
GetOrderItem = pydantic_model_creator(
    OrderItem, name="OrderItem", exclude=("order", "menu_item"),
)

__all__ = [
    "Role", "User", "RefreshToken", "RestaurantType", "Company", "Branch",
    "Employee", "MenuCategory", "MenuItem", "Table", "TableSession",
    "SessionParticipant", "Order", "OrderItem",
    "GetRestaurantType", "GetCompany", "GetBranch",
    "GetCategory", "GetMenuItem", "GetTable", "GetSession",
    "GetParticipant", "GetOrder", "GetOrderItem",
]
