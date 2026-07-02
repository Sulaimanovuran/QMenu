"""Бизнес-логика сотрудников: назначение фиксированной роли в филиале/компании."""
from fastapi import HTTPException, status

from app.models import Employee
from app.common.schemas import CompanyEmployeeIn, EmployeeIn, EmployeeUpdate
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
        branch = await self.repo.get_branch(branch_id)
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        if not await self.repo.get_user(data.user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
        if await self.repo.exists(branch_id, data.user_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Пользователь уже сотрудник филиала"
            )
        role = await self.repo.get_role(data.role_code)
        return await self.repo.create_employee(
            branch_id, branch.company_id, data.user_id, role.id
        )

    async def update_employee(
        self, branch_id: int, employee_id: int, data: EmployeeUpdate
    ) -> Employee:
        emp = await self.repo.get_employee_full(employee_id)
        if not emp or emp.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
        patch = data.model_dump(exclude_unset=True)
        if "role_code" in patch:
            role_code = patch.pop("role_code")
            if role_code not in FIXED_ROLES:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая роль")
            role = await self.repo.get_role(role_code)
            emp.role_id = role.id
        if "status" in patch:
            emp.status = patch["status"]
            emp.is_active = patch["status"] == Employee.ACTIVE
        await emp.save()
        await emp.fetch_related("user", "role")
        return emp

    async def employee_detail(self, employee_id: int) -> Employee:
        emp = await self.repo.get_employee_full(employee_id)
        if not emp:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
        return emp

    async def remove_employee(self, branch_id: int, employee_id: int) -> None:
        emp = await self.repo.get_employee(employee_id)
        if not emp or emp.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сотрудник не найден")
        await self.repo.delete_employee(emp)

    # ── Сотрудники уровня компании ───────────────────────────────────────────
    async def list_company_employees(
        self, company_id: int, limit: int, offset: int, branch_id=None
    ) -> tuple[list[Employee], int]:
        return await self.repo.list_company_employees(company_id, limit, offset, branch_id)

    async def add_company_employee(
        self, company_id: int, data: CompanyEmployeeIn, actor_is_superadmin: bool
    ) -> Employee:
        """Назначение роли уровня компании (branch=None).

        Роль owner может назначить только супер-админ (контракт 8.11);
        branch_admin/kitchen назначаются через branch employees.
        """
        if data.role not in FIXED_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая роль")
        if data.role == "owner" and not actor_is_superadmin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Назначать владельца может только супер-админ"
            )
        if not await self.repo.get_user(data.user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
        role = await self.repo.get_role(data.role)
        if await self.repo.company_role_exists(company_id, data.user_id, role.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "У пользователя уже есть эта роль в компании"
            )
        return await self.repo.create_company_employee(company_id, data.user_id, role.id)

    async def remove_company_employee(self, company_id: int, employee_id: int) -> None:
        emp = await self.repo.get_employee(employee_id)
        if not emp or emp.company_id != company_id or emp.branch_id is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Назначение не найдено")
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
