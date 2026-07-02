from tortoise import fields
from tortoise.models import Model


class Employee(Model):
    """Сотрудник компании/филиала с фиксированной ролью.

    Один User может быть сотрудником нескольких филиалов с разными ролями,
    поэтому связь вынесена в отдельную таблицу (а не поле role на User).

    Роли уровня компании (например будущий company-owner/admin) имеют
    company без branch (branch=None); роли уровня филиала — с branch.
    Уникальность (user, branch, role) обеспечивается в сервис-слое, т.к.
    nullable-поля в unique_together ненадёжны в SQLite.
    """

    ACTIVE = "active"
    BLOCKED = "blocked"

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="employments", on_delete=fields.CASCADE
    )
    company = fields.ForeignKeyField(
        "models.Company", related_name="employees", on_delete=fields.CASCADE
    )
    branch = fields.ForeignKeyField(
        "models.Branch", related_name="employees", null=True, on_delete=fields.CASCADE
    )
    role = fields.ForeignKeyField(
        "models.Role", related_name="employees", on_delete=fields.RESTRICT
    )
    status = fields.CharField(16, default=ACTIVE)   # active | blocked
    is_active = fields.BooleanField(default=True)   # операционный флаг доступа
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "employee"

    def __str__(self) -> str:
        return f"emp:{self.user_id}@branch:{self.branch_id}"
