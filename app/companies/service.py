"""Бизнес-логика: компании и филиалы. Проверки доступа и владения."""
from fastapi import HTTPException, status

from app.models import Company, Branch
from app.common.schemas import CompanyIn, BranchIn, BranchUpdate
from .repository import CompanyRepository


class CompanyService:
    def __init__(self, repo: CompanyRepository):
        self.repo = repo

    # ── Компании ─────────────────────────────────────────────────────────────
    async def list_companies(self, owner_id: int) -> list[Company]:
        return await self.repo.list_companies(owner_id)

    async def create_company(self, data: CompanyIn, owner_id: int) -> Company:
        return await self.repo.create_company(data, owner_id)

    async def get_owned_company(self, company_id: int, owner_id: int) -> Company:
        """Достаёт компанию и проверяет, что её владелец — текущий пользователь."""
        company = await self.repo.get_company(company_id, owner_id)
        if not company:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Компания не найдена")
        return company

    async def delete_company(self, company_id: int, owner_id: int) -> None:
        company = await self.get_owned_company(company_id, owner_id)
        await self.repo.delete_company(company)

    # ── Филиалы ──────────────────────────────────────────────────────────────
    async def list_branches(self, company_id: int, owner_id: int) -> list[Branch]:
        await self.get_owned_company(company_id, owner_id)
        return await self.repo.list_branches(company_id)

    async def create_branch(
        self, company_id: int, data: BranchIn, owner_id: int
    ) -> Branch:
        await self.get_owned_company(company_id, owner_id)
        return await self.repo.create_branch(data, company_id)

    async def update_branch(
        self, company_id: int, branch_id: int, data: BranchUpdate, owner_id: int
    ) -> Branch:
        await self.get_owned_company(company_id, owner_id)
        branch = await self._branch_in_company(branch_id, company_id)
        return await self.repo.update_branch(branch, data)

    async def delete_branch(
        self, company_id: int, branch_id: int, owner_id: int
    ) -> None:
        await self.get_owned_company(company_id, owner_id)
        branch = await self._branch_in_company(branch_id, company_id)
        await self.repo.delete_branch(branch)

    async def _branch_in_company(self, branch_id: int, company_id: int) -> Branch:
        branch = await self.repo.get_branch(branch_id)
        if not branch or branch.company_id != company_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        return branch
