"""Логика заказов: создание гостем (с проверкой прав) и модерация официантом.

Модерация = переход статуса, отдельной очереди-таблицы нет:
    гость создаёт -> pending (кухня НЕ видит)
    официант approve -> approved (попадает на KDS)
    официант reject  -> rejected (с причиной)
    кухня cooking/ready/served — дальнейшие переходы
"""
from fastapi import HTTPException, status

from app.models import Order, TableSession, SessionParticipant
from app.common.schemas import OrderIn, RejectIn
from .repository import OrderRepository


# разрешённые переходы статусов (защита от некорректных смен)
TRANSITIONS: dict[str, set[str]] = {
    Order.APPROVED: {Order.COOKING, Order.CANCELLED},
    Order.COOKING: {Order.READY, Order.CANCELLED},
    Order.READY: {Order.SERVED},
}


class OrderService:
    def __init__(self, repo: OrderRepository):
        self.repo = repo

    # ── Гость ────────────────────────────────────────────────────────────────
    async def create_order(self, session_id: int, device_token: str, data: OrderIn) -> dict:
        session = await TableSession.filter(id=session_id).first()
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        if session.status != TableSession.OPEN:
            raise HTTPException(status.HTTP_409_CONFLICT, "Сессия закрыта")

        participant = await SessionParticipant.filter(
            session_id=session_id, device_token=device_token
        ).first()
        if not participant:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник стола")
        if participant.status not in SessionParticipant.CAN_ORDER:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Хост ещё не подтвердил вас — заказы недоступны",
            )

        order = await self.repo.create_order(session_id, participant.id, data.comment)

        total = 0
        for line in data.items:
            menu_item = await self.repo.get_menu_item(line.menu_item_id)
            if not menu_item:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Позиция {line.menu_item_id} не найдена",
                )
            if menu_item.is_in_stoplist:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"«{menu_item.title}» в стоп-листе",
                )
            await self.repo.add_item(order.id, menu_item, line.qty, line.comment)
            total += menu_item.price_minor * line.qty

        await self.repo.set_total(order, total)
        return await self.order_detail(order.id)

    async def order_detail(self, order_id: int) -> dict:
        order = await self.repo.order_with_items(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
        return self._serialize(order)

    async def list_session_orders(self, session_id: int) -> list[dict]:
        orders = await self.repo.list_by_session(session_id)
        return [self._serialize(o) for o in orders]

    # ── Официант (модерация) ─────────────────────────────────────────────────
    async def moderation_queue(self, branch_id: int) -> list[dict]:
        orders = await self.repo.pending_for_branch(branch_id)
        return [self._serialize(o) for o in orders]

    async def approve(self, branch_id: int, order_id: int, employee_id: int) -> dict:
        order = await self._pending_order(branch_id, order_id)
        order.status = Order.APPROVED
        order.moderated_by_id = employee_id
        await self.repo.save(order)
        return await self.order_detail(order.id)

    async def reject(
        self, branch_id: int, order_id: int, employee_id: int, data: RejectIn
    ) -> dict:
        order = await self._pending_order(branch_id, order_id)
        order.status = Order.REJECTED
        order.reject_reason = data.reason
        order.moderated_by_id = employee_id
        await self.repo.save(order)
        return await self.order_detail(order.id)

    # ── Кухня (KDS) ──────────────────────────────────────────────────────────
    async def kitchen_board(self, branch_id: int) -> list[dict]:
        orders = await self.repo.kitchen_for_branch(branch_id)
        return [self._serialize(o) for o in orders]

    async def change_status(self, branch_id: int, order_id: int, new_status: str) -> dict:
        order = await self.repo.get_order(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
        allowed = TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Недопустимый переход {order.status} -> {new_status}",
            )
        order.status = new_status
        await self.repo.save(order)
        return await self.order_detail(order.id)

    # ── helpers ──────────────────────────────────────────────────────────────
    async def _pending_order(self, branch_id: int, order_id: int) -> Order:
        order = await self.repo.get_order(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
        if order.status != Order.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Заказ уже не на модерации"
            )
        return order

    def _serialize(self, order: Order) -> dict:
        return {
            "id": order.id,
            "session_id": order.session_id,
            "participant_id": order.participant_id,
            "participant_name": getattr(order.participant, "display_name", None)
            if hasattr(order, "participant") and order.participant else None,
            "status": order.status,
            "total_minor": order.total_minor,
            "comment": order.comment,
            "reject_reason": order.reject_reason,
            "items": [
                {
                    "id": it.id,
                    "title": it.title_snapshot,
                    "price_minor": it.price_minor,
                    "qty": it.qty,
                    "comment": it.comment,
                }
                for it in (order.items if hasattr(order, "items") else [])
            ],
        }
