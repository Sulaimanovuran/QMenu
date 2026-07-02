"""Pydantic-схемы запросов, которые не покрываются авто-генерацией из моделей."""
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    login: str
    password: str


# ── Компании / филиалы ───────────────────────────────────────────────────────
class CompanyIn(BaseModel):
    title: str = Field(max_length=50)


class BranchIn(BaseModel):
    title: str = Field(max_length=80)
    address: Optional[str] = None
    moderation_mode: str = Field(default="strict", pattern="^(strict|soft)$")


class BranchUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=80)
    address: Optional[str] = None
    moderation_mode: Optional[str] = Field(default=None, pattern="^(strict|soft)$")
    is_active: Optional[bool] = None


# ── Меню ─────────────────────────────────────────────────────────────────────
class CategoryIn(BaseModel):
    title: str = Field(max_length=80)
    sort_order: int = 0


class MenuItemIn(BaseModel):
    category_id: int
    title: str = Field(max_length=120)
    description: Optional[str] = None
    price_minor: int = Field(ge=0)
    photo_url: Optional[str] = None
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    price_minor: Optional[int] = Field(default=None, ge=0)
    photo_url: Optional[str] = None
    is_in_stoplist: Optional[bool] = None
    sort_order: Optional[int] = None


# ── Столы ────────────────────────────────────────────────────────────────────
class TableIn(BaseModel):
    number: str = Field(max_length=16)
    zone: Optional[str] = None


# ── Сотрудники ───────────────────────────────────────────────────────────────
class EmployeeIn(BaseModel):
    user_id: int
    role_code: str


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


class TableUpdate(BaseModel):
    number: Optional[str] = Field(default=None, max_length=16)
    zone: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=80)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
