"""Эндпоинты заказов: гостевой контур (public), CRM-модерация и KDS.

Контур персонала защищён require_staff_action: пускает супер-админа, владельца
компании и сотрудников с нужной ролью, возвращает employee_id (или None для
владельца/супер-админа) для фиксации исполнителя модерации.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query

from app.common.schemas import CancelIn, OrderIn, RejectIn
from app.common.security import (
    check_branch_access, optional_current_user, require_manage, require_staff_action,
)
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.models import Branch, Employee, Order
from app.models.users import GetUser
from app.users.service import get_current_user
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


@public_order_router.get("/sessions/{session_id}/orders/{order_id}")
async def session_order_detail(
    session_id: int,
    order_id: int,
    x_device_token: str = Header(...),
):
    """Деталка заказа внутри guest-сессии (контрактный путь)."""
    order = await service.order_detail_guarded(order_id, x_device_token, None, False)
    if order["session_id"] != session_id:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Заказ не найден")
    return ok(order)


@public_order_router.post("/sessions/{session_id}/orders/{order_id}/cancel")
async def guest_cancel_order(
    session_id: int,
    order_id: int,
    data: CancelIn,
    x_device_token: str = Header(...),
):
    """Гость отменяет заказ, пока он не ушёл на кухню (pending/approved)."""
    order = await service.cancel_by_guest(session_id, order_id, x_device_token, data.reason)
    return ok(order, "Заказ отменён")


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


# ── CRM: заказы филиала и очередь модерации ───────────────────────────────────
@crm_order_router.get("/branches/{branch_id}/orders")
async def list_branch_orders(
    branch_id: int,
    page: PageParams = Depends(),
    status: Optional[str] = Query(None),
    table_id: Optional[int] = Query(None),
    _: Optional[int] = Depends(MODERATE),
):
    """История/список заказов филиала с фильтрами."""
    items, total = await service.list_branch_orders(
        branch_id, page.limit, page.offset, status, table_id
    )
    return paginated(items, total, page.limit, page.page)


@crm_order_router.get("/orders/{order_id}")
async def crm_order_detail(
    order_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Деталка заказа по id (branch выводится из заказа, доступ проверяется)."""
    order = await service.order_detail(order_id)
    await check_branch_access(order["branch_id"], user, "branch_admin", "waiter", "kitchen")
    return ok(order)


@crm_order_router.get("/branches/{branch_id}/summary")
async def branch_summary(branch_id: int, _=Depends(require_manage("branch_admin", "waiter"))):
    """Сводка филиала: счётчики сессий/заказов/стоп-листа/столов."""
    return ok(await service.branch_summary(branch_id))
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


@crm_order_router.post("/branches/{branch_id}/orders/{order_id}/cancel")
async def cancel_order(
    branch_id: int, order_id: int, data: CancelIn,
    employee_id: Optional[int] = Depends(MODERATE),
):
    """Отмена заказа персоналом (нельзя отменить уже выданный)."""
    order = await service.staff_cancel(branch_id, order_id, employee_id, data.reason)
    return ok(order, "Заказ отменён")


# ── KDS: кухня ────────────────────────────────────────────────────────────────
@kds_order_router.get("/branches/my")
async def kds_my_branches(user: GetUser = Depends(get_current_user)):  # type: ignore
    """Филиалы, доступные кухне текущего пользователя."""
    if user.is_superadmin:
        branches = await Branch.filter(is_active=True).all()
    else:
        emps = (
            await Employee.filter(user_id=user.id, is_active=True, role__code="kitchen")
            .prefetch_related("branch")
            .all()
        )
        branches = [e.branch for e in emps if e.branch and e.branch.is_active]
    return ok([
        {"id": b.id, "title": b.title, "address": b.address, "city": b.city}
        for b in branches
    ])


@kds_order_router.get("/branches/{branch_id}/orders")
async def kitchen_board(
    branch_id: int, page: PageParams = Depends(), _: Optional[int] = Depends(KITCHEN)
):
    """Доска кухни: подтверждённые/готовящиеся/готовые заказы (KdsOrder DTO)."""
    items, total = await service.kitchen_board(branch_id, page.limit, page.offset)
    return paginated(items, total, page.limit, page.page)


@kds_order_router.get("/branches/{branch_id}/orders/{order_id}")
async def kds_order_detail(
    branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)
):
    """Деталка заказа для KDS (без CRM-полей)."""
    return ok(await service.kds_order_detail(branch_id, order_id))


@kds_order_router.post("/branches/{branch_id}/orders/{order_id}/cooking")
async def mark_cooking(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    order = await service.change_status(branch_id, order_id, Order.COOKING)
    return ok(order)


@kds_order_router.post("/branches/{branch_id}/orders/{order_id}/ready")
async def mark_ready(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    order = await service.change_status(branch_id, order_id, Order.READY)
    return ok(order)


@kds_order_router.post("/branches/{branch_id}/orders/{order_id}/served")
async def kds_mark_served(branch_id: int, order_id: int, _: Optional[int] = Depends(KITCHEN)):
    """Кухня отмечает заказ выданным (если выдачу делает кухня, а не зал)."""
    order = await service.change_status(branch_id, order_id, Order.SERVED)
    return ok(order, "Заказ выдан")
