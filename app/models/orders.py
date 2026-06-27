from tortoise import fields
from tortoise.models import Model


class Order(Model):
    """Заказ в рамках сессии стола, сделанный конкретным участником.

    Модерация = статус (простой вариант, без отдельной таблицы-очереди):
        pending   — ждёт подтверждения официантом (НЕ виден кухне)
        approved  — официант подтвердил, ушёл на кухню
        rejected  — официант отклонил (с причиной)
        cooking   — кухня готовит
        ready     — готово, ждёт подачи
        served    — подан
        cancelled — отменён

    Очередь модерации официанта = просто фильтр status=pending по филиалу.
    KDS (кухня) забирает только status in (approved, cooking, ready).
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COOKING = "cooking"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"

    # статусы, видимые кухонному табло
    KITCHEN_STATUSES = (APPROVED, COOKING, READY)

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField(
        "models.TableSession", related_name="orders", on_delete=fields.CASCADE
    )
    participant = fields.ForeignKeyField(
        "models.SessionParticipant", related_name="orders", on_delete=fields.CASCADE
    )
    status = fields.CharField(16, default=PENDING)
    total_minor = fields.IntField(default=0)             # сумма заказа в тыйынах
    comment = fields.TextField(null=True)
    reject_reason = fields.CharField(255, null=True)
    moderated_by = fields.ForeignKeyField(               # официант, обработавший
        "models.Employee", related_name="moderated_orders",
        null=True, on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "order"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"order:{self.id}({self.status})"


class OrderItem(Model):
    """Позиция заказа. Цена фиксируется на момент заказа (price_minor)."""

    id = fields.IntField(pk=True)
    order = fields.ForeignKeyField(
        "models.Order", related_name="items", on_delete=fields.CASCADE
    )
    menu_item = fields.ForeignKeyField(
        "models.MenuItem", related_name="order_items", on_delete=fields.RESTRICT
    )
    title_snapshot = fields.CharField(120)               # копия названия на момент заказа
    price_minor = fields.IntField()                      # копия цены на момент заказа
    qty = fields.IntField(default=1)
    comment = fields.CharField(255, null=True)

    class Meta:
        table = "order_item"

    @property
    def line_total_minor(self) -> int:
        return self.price_minor * self.qty

    def __str__(self) -> str:
        return f"item:{self.title_snapshot}×{self.qty}"
