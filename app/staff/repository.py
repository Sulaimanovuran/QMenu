"""Доступ к данным: сотрудники филиала."""
from typing import Optional

from tortoise.expressions import Q

from app.models import Branch, Employee, Role, User


class StaffRepository:
    async def get_branch(self, branch_id: int) -> Optional[Branch]:
        return await Branch.filter(id=branch_id).first()

    async def list_employees(self, branch_id: int, limit: int, offset: int) -> tuple[list[Employee], int]:
        qs = Employee.filter(branch_id=branch_id)
        total = await qs.count()
        items = (
            await qs.prefetch_related("user", "role")
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    async def get_role(self, code: str) -> Optional[Role]:
        return await Role.filter(code=code).first()

    async def get_user(self, user_id: int) -> Optional[User]:
        return await User.filter(id=user_id).first()

    async def exists(self, branch_id: int, user_id: int) -> bool:
        return await Employee.filter(branch_id=branch_id, user_id=user_id).exists()

    async def create_employee(
        self, branch_id: int, company_id: int, user_id: int, role_id: int
    ) -> Employee:
        emp = await Employee.create(
            branch_id=branch_id, company_id=company_id, user_id=user_id, role_id=role_id
        )
        await emp.fetch_related("user", "role")
        return emp

    async def get_employee(self, employee_id: int) -> Optional[Employee]:
        return await Employee.filter(id=employee_id).first()

    async def get_employee_full(self, employee_id: int) -> Optional[Employee]:
        return (
            await Employee.filter(id=employee_id)
            .prefetch_related("user", "role", "branch", "company")
            .first()
        )

    async def list_company_employees(
        self, company_id: int, limit: int, offset: int,
        branch_id: Optional[int] = None,
    ) -> tuple[list[Employee], int]:
        qs = Employee.filter(company_id=company_id)
        if branch_id is not None:
            qs = qs.filter(branch_id=branch_id)
        total = await qs.count()
        items = (
            await qs.prefetch_related("user", "role", "branch")
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    async def company_role_exists(self, company_id: int, user_id: int, role_id: int) -> bool:
        """Есть ли уже назначение уровня компании (branch=None) с этой ролью."""
        return await Employee.filter(
            company_id=company_id, user_id=user_id, role_id=role_id, branch_id=None
        ).exists()

    async def create_company_employee(
        self, company_id: int, user_id: int, role_id: int
    ) -> Employee:
        emp = await Employee.create(
            company_id=company_id, user_id=user_id, role_id=role_id, branch_id=None
        )
        await emp.fetch_related("user", "role")
        return emp

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
        return (
            await User.filter(
                Q(login__icontains=query) | Q(full_name__icontains=query)
            )
            .limit(limit)
            .all()
        )
