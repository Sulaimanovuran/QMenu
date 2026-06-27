from tortoise import fields
from tortoise.models import Model
from .users import User


class Company(Model):
    """Компания (юрлицо / бренд). Владелец — пользователь User."""

    id = fields.IntField(pk=True)
    title = fields.CharField(50)
    owner = fields.ForeignKeyField(
        "models.User", related_name="companies", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "company"

    def __str__(self) -> str:
        return self.title


class Branch(Model):
    """Филиал / заведение. Принадлежит компании. Меню привязано сюда."""

    id = fields.IntField(pk=True)
    company = fields.ForeignKeyField(
        "models.Company", related_name="branches", on_delete=fields.CASCADE
    )
    title = fields.CharField(80)
    address = fields.CharField(255, null=True)
    # строгий: модерируется каждый заказ; мягкий: доверенные участники — авто
    moderation_mode = fields.CharField(16, default="strict")  # strict | soft
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "branch"

    def __str__(self) -> str:
        return self.title


# Pydantic-схемы создаются в models/__init__.py после init_models,
# чтобы корректно разрешились связи между всеми моделями.
