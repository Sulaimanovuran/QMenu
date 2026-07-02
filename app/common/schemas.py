"""Pydantic-схемы запросов, которые не покрываются авто-генерацией из моделей."""
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    login: str
    password: str


# ── График работы филиала ────────────────────────────────────────────────────
class ScheduleDay(BaseModel):
    day_of_week: int = Field(ge=1, le=7)
    opens_at: str = Field(default="09:00")
    closes_at: str = Field(default="18:00")
    is_closed: bool = False


# ── Компании / филиалы ───────────────────────────────────────────────────────
class CompanyIn(BaseModel):
    title: str = Field(max_length=120)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=255)
    type_codes: list[str] = Field(default_factory=list)
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")
    is_published: bool = False
    is_active: bool = True


class CompanyUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=255)
    type_codes: Optional[list[str]] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|active|archived)$")
    is_published: Optional[bool] = None
    is_active: Optional[bool] = None


class BranchIn(BaseModel):
    title: str = Field(max_length=80)
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    cover_url: Optional[str] = None
    working_hours: Optional[str] = None
    schedule: list[ScheduleDay] = Field(default_factory=list)
    moderation_mode: str = Field(default="strict", pattern="^(strict|auto)$")
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")
    is_published: bool = False
    is_active: bool = True


class BranchUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=80)
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    cover_url: Optional[str] = None
    working_hours: Optional[str] = None
    schedule: Optional[list[ScheduleDay]] = None
    moderation_mode: Optional[str] = Field(default=None, pattern="^(strict|auto)$")
    status: Optional[str] = Field(default=None, pattern="^(draft|active|archived)$")
    is_published: Optional[bool] = None
    is_active: Optional[bool] = None


class BranchSettingsUpdate(BaseModel):
    moderation_mode: Optional[str] = Field(default=None, pattern="^(strict|auto)$")
    allow_guest_join_without_host: Optional[bool] = None
    allow_order_without_approval: Optional[bool] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None


# ── Меню ─────────────────────────────────────────────────────────────────────
class CategoryIn(BaseModel):
    title: str = Field(max_length=80)
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_published: bool = False


class CategoryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=80)
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None


class MenuItemIn(BaseModel):
    category_id: int
    title: str = Field(max_length=120)
    description: Optional[str] = None
    price_minor: int = Field(ge=0)
    image_url: Optional[str] = None
    weight: Optional[int] = Field(default=None, ge=0)
    weight_unit: Optional[str] = Field(default=None, pattern="^(g|ml|pcs)$")
    sort_order: int = 0
    status: str = Field(default="active", pattern="^(active|hidden|stop_list)$")
    is_available: bool = True
    is_published: bool = False
    cooking_zone: str = Field(default="kitchen")


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    price_minor: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    weight: Optional[int] = Field(default=None, ge=0)
    weight_unit: Optional[str] = Field(default=None, pattern="^(g|ml|pcs)$")
    sort_order: Optional[int] = None
    status: Optional[str] = Field(default=None, pattern="^(active|hidden|stop_list)$")
    is_available: Optional[bool] = None
    is_published: Optional[bool] = None
    cooking_zone: Optional[str] = None


class MenuItemAvailability(BaseModel):
    is_available: Optional[bool] = None
    status: Optional[str] = Field(default=None, pattern="^(active|hidden|stop_list)$")


class CategoryReorder(BaseModel):
    category_ids: list[int] = Field(min_length=1)


class ItemReorder(BaseModel):
    category_id: int
    item_ids: list[int] = Field(min_length=1)


class MenuCopyFrom(BaseModel):
    source_branch_id: int
    copy_categories: bool = True
    copy_items: bool = True
    replace_existing: bool = False


# ── Столы ────────────────────────────────────────────────────────────────────
class TableIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=40)
    number: str = Field(max_length=16)
    zone: Optional[str] = None
    seats: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class TableUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=40)
    number: Optional[str] = Field(default=None, max_length=16)
    zone: Optional[str] = None
    seats: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class TableBulkIn(BaseModel):
    zone: Optional[str] = None
    prefix: str = Field(default="", max_length=8)
    from_: int = Field(alias="from", ge=1)
    to: int = Field(ge=1)
    seats: Optional[int] = Field(default=None, ge=1)


# ── Пользователи (CRM) ───────────────────────────────────────────────────────
class UserCreate(BaseModel):
    login: str = Field(max_length=50)
    password: str = Field(min_length=1)
    full_name: str = Field(max_length=100)
    phone: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=1)


# ── Сотрудники ───────────────────────────────────────────────────────────────
class EmployeeIn(BaseModel):
    user_id: int
    role_code: str


class EmployeeUpdate(BaseModel):
    role_code: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|blocked)$")


class CompanyEmployeeIn(BaseModel):
    user_id: int
    role: str


# ── Сессии / участники (гостевой контур) ─────────────────────────────────────
class ScanIn(BaseModel):
    """Гость сканирует QR. device_token хранится у гостя (cookie/localStorage).

    Если токена ещё нет — клиент шлёт null, сервер сгенерирует и вернёт.
    """
    qr_token: str
    device_token: Optional[str] = None
    display_name: Optional[str] = Field(default=None, max_length=40)


class JoinDecision(BaseModel):
    """Хост подтверждает/отклоняет участника."""
    participant_id: int
    approve: bool


class ParticipantDecide(BaseModel):
    """Решение по участнику (CRM/host): approved | rejected."""
    decision: str = Field(pattern="^(approved|rejected)$")


class ParticipantRename(BaseModel):
    name: str = Field(max_length=40)


# ── Заказы ───────────────────────────────────────────────────────────────────
class OrderLineIn(BaseModel):
    menu_item_id: int
    qty: int = Field(ge=1)
    comment: Optional[str] = Field(default=None, max_length=255)


class OrderIn(BaseModel):
    """Гость оформляет заказ внутри своей сессии."""
    device_token: str
    comment: Optional[str] = None
    items: list[OrderLineIn] = Field(min_length=1)


class RejectIn(BaseModel):
    reason: str = Field(max_length=255)


class CancelIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=255)
