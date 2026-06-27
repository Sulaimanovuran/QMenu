"""Доступ к данным: заказы и позиции заказа."""
from typing import Optional

from app.models import Order, OrderItem, MenuItem


class OrderRepository:
    async def create_order(
        self, session_id: int, participant_id: int, comment: Optional[str]
    ) -> Order:
        return await Order.create(
            session_id=session_id, participant_id=participant_id, comment=comment
        )

    async def add_item(
        self, order_id: int, menu_item: MenuItem, qty: int, comment: Optional[str]
    ) -> OrderItem:
        return await OrderItem.create(
            order_id=order_id,
            menu_item_id=menu_item.id,
            title_snapshot=menu_item.title,
            price_minor=menu_item.price_minor,
            qty=qty,
            comment=comment,
        )

    async def set_total(self, order: Order, total_minor: int) -> None:
        order.total_minor = total_minor
        await order.save()

    async def get_order(self, order_id: int) -> Optional[Order]:
        return await Order.filter(id=order_id).first()

    async def get_menu_item(self, item_id: int) -> Optional[MenuItem]:
        return await MenuItem.filter(id=item_id).first()

    async def order_with_items(self, order_id: int) -> Optional[Order]:
        return (
            await Order.filter(id=order_id)
            .prefetch_related("items", "participant")
            .first()
        )

    async def list_by_session(self, session_id: int) -> list[Order]:
        return (
            await Order.filter(session_id=session_id)
            .prefetch_related("items", "participant")
            .all()
        )

    async def pending_for_branch(self, branch_id: int) -> list[Order]:
        """Очередь модерации: pending-заказы всех открытых сессий филиала."""
        return (
            await Order.filter(
                status=Order.PENDING, session__table__branch_id=branch_id
            )
            .prefetch_related("items", "participant", "session")
            .all()
        )

    async def kitchen_for_branch(self, branch_id: int) -> list[Order]:
        """Для KDS: заказы, ушедшие на кухню (approved/cooking/ready)."""
        return (
            await Order.filter(
                status__in=Order.KITCHEN_STATUSES,
                session__table__branch_id=branch_id,
            )
            .prefetch_related("items", "session")
            .all()
        )

    async def save(self, order: Order) -> None:
        await order.save()
