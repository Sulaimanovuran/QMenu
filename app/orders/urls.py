"""Эндпоинты заказов: гостевой контур + контур персонала (модерация, KDS).

Контур персонала защищён require_staff_action: пускает владельца компании и
сотрудников с нужной ролью, возвращает employee_id (или None для владельца)
для фиксации исполнителя модерации.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.common.schemas import OrderIn, RejectIn
from app.common.security import require_staff_action, optional_current_user
from app.models import Order
from .service import OrderService
from .repository import OrderRepository

orderRouter = APIRouter()
service = OrderService(OrderRepository())

# модерация — официанты/старшие/менеджеры/админы; KDS — кухня + те же
MODERATE = require_staff_action("admin", "manager", "senior_waiter", "waiter")
KITCHEN = require_staff_action("admin", "manager", "senior_waiter", "kitchen")


# ── Гость ────────────────────────────────────────────────────────────────────
@orderRouter.post("/sessions/{session_id}/orders")
async def create_order(
    session_id: int, data: OrderIn, x_device_token: str = Header(...)
):
    """Гость оформляет заказ. device_token должен совпадать с телом запроса."""
    return await service.create_order(session_id, x_device_token, data)


@orderRouter.get("/sessions/{session_id}/orders")
async def list_session_orders(session_id: int):
    """Все заказы сессии (экран «кто что заказал»)."""
    return await service.list_session_orders(session_id)


@orderRouter.get("/{order_id}")
async def order_detail(
    order_id: int,
    x_device_token: Optional[str] = Header(None),
    user=Depends(optional_current_user),
):
    """Детали заказа. Доступ: участник сессии (X-Device-Token) или персонал (JWT)."""
    user_id = user.id if user else None
    return await service.order_detail_guarded(order_id, x_device_token, user_id)


# ── Официант: очередь модерации ──────────────────────────────────────────────
@orderRouter.get("/branches/{branch_id}/moderation")
async def moderation_queue(branch_id: int, _: Optional[int] = Depends(MODERATE)):
    """Заказы на модерации (status=pending) по филиалу."""
    return await service.moderation_queue(branch_id)


@orderRouter.post("/branches/{branch_id}/orders/{order_id}/approve")
async def approve_order(
    branch_id: int, order_id: int, employee_id: Optional[int] = Depends(MODERATE)
):
    """Официант подтверждает заказ -> уходит на кухню."""
    return await service.approve(branch_id, order_id, employee_id)


@orderRouter.post("/branches/{branch_id}/orders/{order_id}/reject")
async def reject_order(
    branch_id: int, order_id: int, data: RejectIn,
    employee_id: Optional[int] = Depends(MODERATE),
):
    """Официант отклоняет заказ с причиной."""
    return await service.reject(branch_id, order_id, employee_id, data)


# ── Кухня: KDS ───────────────────────────────────────────────────────────────
@orderRouter.get("/branches/{branch_id}/kitchen")
async def kitchen_board(branch_id: int, _: Optional[int] = Depends(KITCHEN)):
    """Доска кухни: подтверждённые/готовящиеся/готовые заказы."""
    return await service.kitchen_board(branch_id)


@orderRouter.post("/branches/{branch_id}/orders/{order_id}/cooking")
async def mark_cooking(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    return await service.change_status(branch_id, order_id, Order.COOKING)


@orderRouter.post("/branches/{branch_id}/orders/{order_id}/ready")
async def mark_ready(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    return await service.change_status(branch_id, order_id, Order.READY)


@orderRouter.post("/branches/{branch_id}/orders/{order_id}/served")
async def mark_served(branch_id: int, order_id: int, _: Optional[int] = Depends(MODERATE)):
    return await service.change_status(branch_id, order_id, Order.SERVED)
