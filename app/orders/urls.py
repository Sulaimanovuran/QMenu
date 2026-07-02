"""Эндпоинты заказов: гостевой контур (public), CRM-модерация и KDS.

Контур персонала защищён require_staff_action: пускает супер-админа, владельца
компании и сотрудников с нужной ролью, возвращает employee_id (или None для
владельца/супер-админа) для фиксации исполнителя модерации.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.common.schemas import OrderIn, RejectIn
from app.common.security import require_staff_action, optional_current_user
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.models import Order
from .service import OrderService
from .repository import OrderRepository

public_order_router = APIRouter()
crm_order_router = APIRouter()
kds_order_router = APIRouter()

service = OrderService(OrderRepository())

# модерация/CRM — branch_admin и waiter (у официанта прав меньше: он не может
# управлять меню/столами/сотрудниками — см. MANAGE в menu/tables/urls.py и
# require_branch_owner в staff/urls.py); KDS — kitchen.
# Владелец/супер-админ проходят отдельной веткой внутри require_staff_action.
MODERATE = require_staff_action("branch_admin", "waiter")
KITCHEN = require_staff_action("kitchen")


# ── Гость (public) ────────────────────────────────────────────────────────────
@public_order_router.post("/sessions/{session_id}/orders")
async def create_order(
    session_id: int, data: OrderIn, x_device_token: str = Header(...)
):
    """Гость оформляет заказ. device_token должен совпадать с телом запроса."""
    order = await service.create_order(session_id, x_device_token, data)
    return ok(order, "Заказ создан")


@public_order_router.get("/sessions/{session_id}/orders")
async def list_session_orders(session_id: int, page: PageParams = Depends()):
    """Все заказы сессии (экран «кто что заказал»)."""
    items, total = await service.list_session_orders(session_id, page.limit, page.offset)
    return paginated(items, total, page.limit, page.page)


@public_order_router.get("/{order_id}")
async def order_detail(
    order_id: int,
    x_device_token: Optional[str] = Header(None),
    user=Depends(optional_current_user),
):
    """Детали заказа. Доступ: участник сессии (X-Device-Token) или персонал (JWT)."""
    user_id = user.id if user else None
    is_superadmin = bool(user and getattr(user, "is_superadmin", False))
    order = await service.order_detail_guarded(order_id, x_device_token, user_id, is_superadmin)
    return ok(order)


# ── CRM: очередь модерации ────────────────────────────────────────────────────
@crm_order_router.get("/branches/{branch_id}/moderation")
async def moderation_queue(
    branch_id: int, page: PageParams = Depends(), _: Optional[int] = Depends(MODERATE)
):
    """Заказы на модерации (status=pending) по филиалу."""
    items, total = await service.moderation_queue(branch_id, page.limit, page.offset)
    return paginated(items, total, page.limit, page.page)


@crm_order_router.post("/branches/{branch_id}/orders/{order_id}/approve")
async def approve_order(
    branch_id: int, order_id: int, employee_id: Optional[int] = Depends(MODERATE)
):
    """Официант/администратор филиала подтверждает заказ -> уходит на кухню."""
    order = await service.approve(branch_id, order_id, employee_id)
    return ok(order, "Заказ подтверждён")


@crm_order_router.post("/branches/{branch_id}/orders/{order_id}/reject")
async def reject_order(
    branch_id: int, order_id: int, data: RejectIn,
    employee_id: Optional[int] = Depends(MODERATE),
):
    """Администратор филиала отклоняет заказ с причиной."""
    order = await service.reject(branch_id, order_id, employee_id, data)
    return ok(order, "Заказ отклонён")


@crm_order_router.post("/branches/{branch_id}/orders/{order_id}/served")
async def mark_served(branch_id: int, order_id: int, _: Optional[int] = Depends(MODERATE)):
    order = await service.change_status(branch_id, order_id, Order.SERVED)
    return ok(order, "Заказ выдан")


# ── KDS: кухня ────────────────────────────────────────────────────────────────
@kds_order_router.get("/branches/{branch_id}/orders")
async def kitchen_board(
    branch_id: int, page: PageParams = Depends(), _: Optional[int] = Depends(KITCHEN)
):
    """Доска кухни: подтверждённые/готовящиеся/готовые заказы."""
    items, total = await service.kitchen_board(branch_id, page.limit, page.offset)
    return paginated(items, total, page.limit, page.page)


@kds_order_router.post("/branches/{branch_id}/orders/{order_id}/cooking")
async def mark_cooking(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    order = await service.change_status(branch_id, order_id, Order.COOKING)
    return ok(order)


@kds_order_router.post("/branches/{branch_id}/orders/{order_id}/ready")
async def mark_ready(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    order = await service.change_status(branch_id, order_id, Order.READY)
    return ok(order)
