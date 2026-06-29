from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator


class Role(Model):
    """Фиксированные роли сотрудников.

    Набор ролей задан кодом (см. enum RoleCode) и сидируется при старте.
    Произвольный конструктор прав сознательно не делаем (решение по ТЗ).
    """

    id = fields.IntField(pk=True)
    code = fields.CharField(32, unique=True)   # owner / admin / manager / senior_waiter / waiter / kitchen
    title = fields.CharField(64)               # человекочитаемое название

    class Meta:
        table = "role"

    def __str__(self) -> str:
        return self.code


GetRole = pydantic_model_creator(Role, name="Role")
