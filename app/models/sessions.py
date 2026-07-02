from tortoise import fields
from tortoise.models import Model


class TableSession(Model):
    """Сессия стола (визит). Один общий чек на стол (гибрид: см. participants).

    Жизненный цикл:
        open    — активный визит, можно делать заказы
        closed  — счёт закрыт/оплачен, новые заказы запрещены

    Хост (первый отсканировавший QR, «главный») определяется участником со
    status="host". Ссылка на него хранится как host_participant_id —
    обычным int-полем, а не ForeignKeyField, чтобы избежать циклической
    FK-зависимости TableSession <-> SessionParticipant (Tortoise не создаёт
    схему при циклах). Целостность поддерживается на уровне сервиса.
    """

    OPEN = "open"
    CLOSED = "closed"

    id = fields.IntField(pk=True)
    table = fields.ForeignKeyField(
        "models.Table", related_name="sessions", on_delete=fields.CASCADE
    )
    status = fields.CharField(16, default=OPEN)          # open | closed
    host_participant_id = fields.IntField(null=True)     # «мягкая» ссылка на хоста
    opened_at = fields.DatetimeField(auto_now_add=True)
    closed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "table_session"

    def __str__(self) -> str:
        return f"session:{self.id}({self.status})"


class SessionParticipant(Model):
    """Участник стола в рамках одной сессии.

    Каждому гостю-браузеру выдаётся анонимный device_token (cookie/localStorage).
    Статус управляет допуском к заказам (mCafe-подтверждение хостом):
        host      — главный, подтверждает остальных
        pending   — отсканировал QR, ждёт подтверждения хоста
        approved  — допущен, может делать заказы
        rejected  — отклонён хостом
    """

    HOST = "host"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LEFT = "left"

    # статусы, при которых участник может делать заказы
    CAN_ORDER = (HOST, APPROVED)

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField(
        "models.TableSession", related_name="participants", on_delete=fields.CASCADE
    )
    device_token = fields.CharField(64)                  # анонимный токен устройства
    display_name = fields.CharField(40, null=True)       # «Гость 2», опц.
    status = fields.CharField(16, default=PENDING)       # host|pending|approved|rejected
    joined_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "session_participant"
        unique_together = (("session", "device_token"),)

    def __str__(self) -> str:
        return f"participant:{self.id}({self.status})"
