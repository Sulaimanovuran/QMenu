from tortoise import fields
from tortoise.models import Model


class MenuCategory(Model):
    """Категория меню филиала (Горячее, Напитки и т.д.)."""

    id = fields.IntField(pk=True)
    branch = fields.ForeignKeyField(
        "models.Branch", related_name="categories", on_delete=fields.CASCADE
    )
    slug = fields.CharField(140, null=True)
    title = fields.CharField(80)
    description = fields.TextField(null=True)
    image_url = fields.CharField(255, null=True)
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    is_published = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "menu_category"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class MenuItem(Model):
    """Блюдо / напиток. Цена в минимальных единицах (тыйын) во избежание float.

    price_minor хранит сумму в тыйынах: 420.00 сом -> 42000.
    """

    ACTIVE = "active"
    HIDDEN = "hidden"
    STOP_LIST = "stop_list"

    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField(
        "models.MenuCategory", related_name="items", on_delete=fields.CASCADE
    )
    title = fields.CharField(120)
    description = fields.TextField(null=True)
    price_minor = fields.IntField()                 # цена в тыйынах
    image_url = fields.CharField(255, null=True)
    weight = fields.IntField(null=True)             # граммовка / объём
    weight_unit = fields.CharField(8, null=True)    # g | ml | pcs
    sort_order = fields.IntField(default=0)
    status = fields.CharField(16, default=ACTIVE)   # active | hidden | stop_list
    is_available = fields.BooleanField(default=True)
    is_published = fields.BooleanField(default=False)
    cooking_zone = fields.CharField(16, default="kitchen")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "menu_item"
        ordering = ["sort_order", "id"]

    @property
    def is_in_stoplist(self) -> bool:
        """Совместимость со старой логикой заказов: недоступно к заказу."""
        return self.status == self.STOP_LIST or not self.is_available

    def __str__(self) -> str:
        return self.title
