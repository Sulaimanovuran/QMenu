from tortoise import fields
from tortoise.models import Model
from .users import User


class Company(Model):
    """Компания (юрлицо / бренд). Владелец — пользователь User.

    На guest-главной отображается как карточка заведения (public place).
    """

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

    id = fields.IntField(pk=True)
    slug = fields.CharField(120, unique=True)
    title = fields.CharField(120)
    description = fields.TextField(null=True)
    short_description = fields.CharField(255, null=True)
    # список кодов типов заведения (RestaurantType.code), напр. ["coffee","restaurant"]
    type_codes = fields.JSONField(default=list)
    logo_url = fields.CharField(255, null=True)
    cover_url = fields.CharField(255, null=True)
    owner = fields.ForeignKeyField(
        "models.User", related_name="companies", on_delete=fields.CASCADE
    )
    status = fields.CharField(16, default=DRAFT)   # draft | active | archived
    is_active = fields.BooleanField(default=True)
    is_published = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "company"

    def __str__(self) -> str:
        return self.title


class Branch(Model):
    """Филиал / заведение. Принадлежит компании. Меню привязано сюда."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

    id = fields.IntField(pk=True)
    company = fields.ForeignKeyField(
        "models.Company", related_name="branches", on_delete=fields.CASCADE
    )
    slug = fields.CharField(140, unique=True)
    title = fields.CharField(80)
    address = fields.CharField(255, null=True)
    city = fields.CharField(80, null=True)
    latitude = fields.FloatField(null=True)
    longitude = fields.FloatField(null=True)
    phone = fields.CharField(20, null=True)
    cover_url = fields.CharField(255, null=True)
    # готовый текст для UI, напр. "09:00 - 00:00"
    working_hours = fields.CharField(80, null=True)
    # структурный график: [{day_of_week, opens_at, closes_at, is_closed}, ...]
    schedule = fields.JSONField(default=list)
    # strict: модерируется каждый заказ; auto: заказ сразу уходит на кухню
    moderation_mode = fields.CharField(16, default="strict")  # strict | auto
    # можно ли гостю сразу становиться approved (без подтверждения хостом)
    allow_guest_join_without_host = fields.BooleanField(default=False)
    # можно ли pending-гостю отправлять заказ
    allow_order_without_approval = fields.BooleanField(default=False)
    status = fields.CharField(16, default=DRAFT)   # draft | active | archived
    is_active = fields.BooleanField(default=True)
    is_published = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "branch"

    def __str__(self) -> str:
        return self.title


# Pydantic-схемы создаются в models/__init__.py после init_models,
# чтобы корректно разрешились связи между всеми моделями.
