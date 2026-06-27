"""Слой доступа к данным: компании и филиалы. Только запросы к БД."""
from typing import Optional

from app.models import Company, Branch
from app.common.schemas import CompanyIn, BranchIn, BranchUpdate


class CompanyRepository:
    # ── Компании ─────────────────────────────────────────────────────────────
    async def list_companies(self, owner_id: int) -> list[Company]:
        return await Company.filter(owner_id=owner_id).all()

    async def get_company(self, company_id: int, owner_id: int) -> Optional[Company]:
        return await Company.filter(id=company_id, owner_id=owner_id).first()

    async def create_company(self, data: CompanyIn, owner_id: int) -> Company:
        return await Company.create(title=data.title, owner_id=owner_id)

    async def delete_company(self, company: Company) -> None:
        await company.delete()

    # ── Филиалы ──────────────────────────────────────────────────────────────
    async def list_branches(self, company_id: int) -> list[Branch]:
        return await Branch.filter(company_id=company_id).all()

    async def get_branch(self, branch_id: int) -> Optional[Branch]:
        return await Branch.filter(id=branch_id).first()

    async def create_branch(self, data: BranchIn, company_id: int) -> Branch:
        return await Branch.create(
            company_id=company_id,
            title=data.title,
            address=data.address,
            moderation_mode=data.moderation_mode,
        )

    async def update_branch(self, branch: Branch, data: BranchUpdate) -> Branch:
        patch = data.model_dump(exclude_unset=True)
        for field, value in patch.items():
            setattr(branch, field, value)
        await branch.save()
        return branch

    async def delete_branch(self, branch: Branch) -> None:
        await branch.delete()
