from tortoise import fields
from tortoise.models import Model


class Table(Model):
    """Стол в филиале. qr_token зашит в QR-ссылку и публично сканируется."""

    id = fields.IntField(pk=True)
    branch = fields.ForeignKeyField(
        "models.Branch", related_name="tables", on_delete=fields.CASCADE
    )
    title = fields.CharField(40, null=True)             # «A-5»
    number = fields.CharField(16)                       # «12», «VIP-3»
    zone = fields.CharField(40, null=True)              # зал / терраса
    seats = fields.IntField(null=True)                  # число мест
    qr_token = fields.CharField(64, unique=True)        # секрет в QR
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "restaurant_table"
        unique_together = (("branch", "number"),)

    def __str__(self) -> str:
        return f"table:{self.number}@branch:{self.branch_id}"
