from tortoise import fields
from tortoise.models import Model


class Employee(Model):
    """Сотрудник в конкретном филиале с фиксированной ролью.

    Один User может быть сотрудником в нескольких филиалах с разными ролями,
    поэтому связь вынесена в отдельную таблицу (а не поле role на User).
    """

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="employments", on_delete=fields.CASCADE
    )
    branch = fields.ForeignKeyField(
        "models.Branch", related_name="employees", on_delete=fields.CASCADE
    )
    role = fields.ForeignKeyField(
        "models.Role", related_name="employees", on_delete=fields.RESTRICT
    )
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "employee"
        unique_together = (("user", "branch"),)  # один человек — одна запись на филиал

    def __str__(self) -> str:
        return f"emp:{self.user_id}@branch:{self.branch_id}"
