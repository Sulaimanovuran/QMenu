"""Логика заказов: создание гостем (с проверкой прав) и модерация официантом.

Модерация = переход статуса, отдельной очереди-таблицы нет:
    гость создаёт -> pending (кухня НЕ видит)
    официант approve -> approved (попадает на KDS)
    официант reject  -> rejected (с причиной)
    кухня cooking/ready/served — дальнейшие переходы

Все действия персонала проверяют, что заказ принадлежит указанному филиалу
(order -> session -> table -> branch_id == branch_id).
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
        session = (
            await TableSession.filter(id=session_id)
            .prefetch_related("table")
            .first()
        )
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

        branch_id = session.table.branch_id

        # сначала валидируем все позиции, только потом создаём заказ
        validated: list[tuple] = []  # (menu_item, qty, comment)
        for line in data.items:
            if line.qty <= 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "Количество должно быть больше 0"
                )
            menu_item = await self.repo.get_menu_item(line.menu_item_id)
            if not menu_item:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Позиция {line.menu_item_id} не найдена",
                )
            # позиция должна принадлежать тому же филиалу, что и стол
            if menu_item.category.branch_id != branch_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Позиция «{menu_item.title}» из другого филиала",
                )
            if menu_item.is_in_stoplist:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, f"«{menu_item.title}» в стоп-листе"
                )
            validated.append((menu_item, line.qty, line.comment))

        order = await self.repo.create_order(session_id, participant.id, data.comment)
        total = 0
        for menu_item, qty, comment in validated:
            await self.repo.add_item(order.id, menu_item, qty, comment)
            total += menu_item.price_minor * qty
        await self.repo.set_total(order, total)
        return await self.order_detail(order.id)

    async def order_detail(self, order_id: int) -> dict:
        order = await self.repo.order_with_items(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
        return self._serialize(order)

    async def order_detail_guarded(
        self,
        order_id: int,
        device_token: str | None,
        user_id: int | None,
        is_superadmin: bool = False,
    ) -> dict:
        """Детали заказа с проверкой доступа: участник сессии ИЛИ сотрудник/владелец/супер-админ.

        device_token — для гостя (участника сессии заказа).
        user_id — для персонала: сотрудник филиала, владелец компании или супер-админ.
        """
        from app.models import SessionParticipant, Employee, Branch

        order = await self.repo.order_with_items(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")

        # 1) гость — участник этой сессии
        if device_token:
            is_participant = await SessionParticipant.filter(
                session_id=order.session_id, device_token=device_token
            ).exists()
            if is_participant:
                return self._serialize(order)

        # 2) персонал — супер-админ, сотрудник филиала или владелец компании
        if user_id is not None:
            if is_superadmin:
                return self._serialize(order)
            branch_id = order.session.table.branch_id
            is_staff = await Employee.filter(
                user_id=user_id, branch_id=branch_id, is_active=True
            ).exists()
            if is_staff:
                return self._serialize(order)
            branch = await Branch.filter(id=branch_id).prefetch_related("company").first()
            if branch and branch.company.owner_id == user_id:
                return self._serialize(order)

        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к этому заказу")

    async def list_session_orders(self, session_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
        orders, total = await self.repo.list_by_session(session_id, limit, offset)
        return [self._serialize(o) for o in orders], total

    # ── Официант (модерация) ─────────────────────────────────────────────────
    async def moderation_queue(self, branch_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
        orders, total = await self.repo.pending_for_branch(branch_id, limit, offset)
        return [self._serialize(o) for o in orders], total

    async def approve(self, branch_id: int, order_id: int, employee_id) -> dict:
        order = await self._pending_order(branch_id, order_id)
        order.status = Order.APPROVED
        order.moderated_by_id = employee_id
        await self.repo.save(order)
        return await self.order_detail(order.id)

    async def reject(self, branch_id: int, order_id: int, employee_id, data: RejectIn) -> dict:
        order = await self._pending_order(branch_id, order_id)
        order.status = Order.REJECTED
        order.reject_reason = data.reason
        order.moderated_by_id = employee_id
        await self.repo.save(order)
        return await self.order_detail(order.id)

    # ── Кухня (KDS) ──────────────────────────────────────────────────────────
    async def kitchen_board(self, branch_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
        orders, total = await self.repo.kitchen_for_branch(branch_id, limit, offset)
        return [self._serialize(o) for o in orders], total

    async def change_status(self, branch_id: int, order_id: int, new_status: str) -> dict:
        order = await self._order_in_branch(branch_id, order_id)
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
    async def _order_in_branch(self, branch_id: int, order_id: int) -> Order:
        """Заказ + жёсткая проверка принадлежности филиалу."""
        order = await self.repo.get_order(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
        if order.session.table.branch_id != branch_id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Заказ не принадлежит этому филиалу"
            )
        return order

    async def _pending_order(self, branch_id: int, order_id: int) -> Order:
        order = await self._order_in_branch(branch_id, order_id)
        if order.status != Order.PENDING:
            raise HTTPException(status.HTTP_409_CONFLICT, "Заказ уже не на модерации")
        return order

    def _serialize(self, order: Order) -> dict:
        table = None
        if order.session and order.session.table:
            t = order.session.table
            table = {"id": t.id, "number": t.number, "zone": t.zone}
        participant = None
        if order.participant:
            participant = {
                "id": order.participant.id,
                "name": order.participant.display_name,
            }
        return {
            "id": order.id,
            "branch_id": order.session.table.branch_id
            if order.session and order.session.table else None,
            "session_id": order.session_id,
            "table": table,
            "participant": participant,
            # сохраняем плоские поля для обратной совместимости с фронтом
            "participant_id": order.participant_id,
            "participant_name": order.participant.display_name if order.participant else None,
            "status": order.status,
            "total_minor": order.total_minor,
            "comment": order.comment,
            "reject_reason": order.reject_reason,
            # кто обработал модерацию (branch_admin/waiter -> их employee_id;
            # владелец/супер-админ без записи employee -> None)
            "moderated_by": order.moderated_by_id,
            "items": [
                {
                    "id": it.id,
                    "menu_item_id": it.menu_item_id,
                    "title": it.title_snapshot,
                    "price_minor": it.price_minor,
                    "qty": it.qty,
                    "comment": it.comment,
                }
                for it in order.items
            ],
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }
