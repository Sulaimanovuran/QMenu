"""Бизнес-логика сотрудников: назначение фиксированной роли в филиале."""
from fastapi import HTTPException, status

from app.models import Employee
from app.common.schemas import EmployeeIn
from app.common.roles import FIXED_ROLES
from .repository import StaffRepository


class StaffService:
    def __init__(self, repo: StaffRepository):
        self.repo = repo

    async def list_employees(self, branch_id: int, limit: int, offset: int) -> tuple[list[Employee], int]:
        return await self.repo.list_employees(branch_id, limit, offset)

    async def add_employee(self, branch_id: int, data: EmployeeIn) -> Employee:
        if data.role_code not in FIXED_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая роль")
        if not await self.repo.get_user(data.user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
        if await self.repo.exists(branch_id, data.user_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Пользователь уже сотрудник филиала"
            )
        role = await self.repo.get_role(data.role_code)
        return await self.repo.create_employee(branch_id, data.user_id, role.id)

    async def remove_employee(self, branch_id: int, employee_id: int) -> None:
        emp = await self.repo.get_employee(employee_id)
        if not emp or emp.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
        await self.repo.delete_employee(emp)

    async def my_branches(self, user_id: int) -> list[dict]:
        emps = await self.repo.my_branches(user_id)
        result = []
        for e in emps:
            b = e.branch
            result.append({
                "company_id": b.company.id,
                "company_title": b.company.title,
                "branch_id": b.id,
                "branch_title": b.title,
                "address": b.address,
                "role_code": e.role.code,
                "is_active": e.is_active,
                "moderation_mode": b.moderation_mode,
            })
        return result

    async def search_users(self, query: str) -> list[dict]:
        users = await self.repo.search_users(query)
        return [{"id": u.id, "login": u.login, "full_name": u.full_name} for u in users]
