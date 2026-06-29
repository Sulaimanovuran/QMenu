"""Доступ к данным: сотрудники филиала."""
from typing import Optional

from app.models import Employee, Role, User


class StaffRepository:
    async def list_employees(self, branch_id: int) -> list[Employee]:
        return (
            await Employee.filter(branch_id=branch_id)
            .prefetch_related("user", "role")
            .all()
        )

    async def get_role(self, code: str) -> Optional[Role]:
        return await Role.filter(code=code).first()

    async def get_user(self, user_id: int) -> Optional[User]:
        return await User.filter(id=user_id).first()

    async def exists(self, branch_id: int, user_id: int) -> bool:
        return await Employee.filter(branch_id=branch_id, user_id=user_id).exists()

    async def create_employee(
        self, branch_id: int, user_id: int, role_id: int
    ) -> Employee:
        emp = await Employee.create(
            branch_id=branch_id, user_id=user_id, role_id=role_id
        )
        await emp.fetch_related("user", "role")
        return emp

    async def get_employee(self, employee_id: int) -> Optional[Employee]:
        return await Employee.filter(id=employee_id).first()

    async def delete_employee(self, employee: Employee) -> None:
        await employee.delete()

    async def my_branches(self, user_id: int):
        """Филиалы, где пользователь — активный сотрудник (с ролью и компанией)."""
        return (
            await Employee.filter(user_id=user_id, is_active=True)
            .prefetch_related("role", "branch__company")
            .all()
        )

    async def search_users(self, query: str, limit: int = 20):
        return await User.filter(name__icontains=query).limit(limit).all()
