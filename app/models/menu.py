from tortoise import fields
from tortoise.models import Model


class MenuCategory(Model):
    """Категория меню филиала (Горячее, Напитки и т.д.)."""

    id = fields.IntField(pk=True)
    branch = fields.ForeignKeyField(
        "models.Branch", related_name="categories", on_delete=fields.CASCADE
    )
    title = fields.CharField(80)
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "menu_category"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class MenuItem(Model):
    """Блюдо / напиток. Цена в минимальных единицах (тыйын) во избежание float.

    price_minor хранит сумму в тыйынах: 420.00 сом -> 42000.
    """

    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField(
        "models.MenuCategory", related_name="items", on_delete=fields.CASCADE
    )
    title = fields.CharField(120)
    description = fields.TextField(null=True)
    price_minor = fields.IntField()                 # цена в тыйынах
    photo_url = fields.CharField(255, null=True)
    is_in_stoplist = fields.BooleanField(default=False)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "menu_item"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title
