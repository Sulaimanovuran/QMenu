"""Справочник типов заведений (кофейня, ресторан, чайхана и т.д.)."""
from tortoise import fields
from tortoise.models import Model


class RestaurantType(Model):
    id = fields.IntField(pk=True)
    code = fields.CharField(40, unique=True)      # coffee, restaurant, chaikhana
    title = fields.CharField(80)
    image_url = fields.CharField(255, null=True)
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "restaurant_type"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.code
