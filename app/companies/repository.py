"""Слой доступа к данным: компании и филиалы. Только запросы к БД."""
from typing import Optional

from app.models import Company, Branch
from app.common.schemas import CompanyIn, BranchIn, BranchUpdate
from app.common.slug import unique_slug


class CompanyRepository:
    # ── Компании ─────────────────────────────────────────────────────────────
    async def list_companies(
        self, owner_id: Optional[int], limit: int, offset: int
    ) -> tuple[list[Company], int]:
        qs = Company.all() if owner_id is None else Company.filter(owner_id=owner_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def get_company(self, company_id: int, owner_id: Optional[int]) -> Optional[Company]:
        qs = Company.filter(id=company_id)
        if owner_id is not None:
            qs = qs.filter(owner_id=owner_id)
        return await qs.first()

    async def create_company(self, data: CompanyIn, owner_id: int) -> Company:
        slug = await unique_slug(Company, data.title)
        return await Company.create(
            slug=slug,
            title=data.title,
            description=data.description,
            short_description=data.short_description,
            type_codes=data.type_codes,
            logo_url=data.logo_url,
            cover_url=data.cover_url,
            owner_id=owner_id,
            status=data.status,
            is_published=data.is_published,
            is_active=data.is_active,
        )

    async def update_company(self, company: Company, patch: dict) -> Company:
        for field, value in patch.items():
            setattr(company, field, value)
        await company.save()
        return company

    async def delete_company(self, company: Company) -> None:
        await company.delete()

    # ── Филиалы ──────────────────────────────────────────────────────────────
    async def list_branches(self, company_id: int, limit: int, offset: int) -> tuple[list[Branch], int]:
        qs = Branch.filter(company_id=company_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def get_branch(self, branch_id: int) -> Optional[Branch]:
        return await Branch.filter(id=branch_id).first()

    async def create_branch(self, data: BranchIn, company_id: int) -> Branch:
        slug = await unique_slug(Branch, data.title)
        schedule = [d.model_dump() for d in data.schedule]
        return await Branch.create(
            company_id=company_id,
            slug=slug,
            title=data.title,
            address=data.address,
            city=data.city,
            latitude=data.latitude,
            longitude=data.longitude,
            phone=data.phone,
            cover_url=data.cover_url,
            working_hours=data.working_hours,
            schedule=schedule,
            moderation_mode=data.moderation_mode,
            status=data.status,
            is_published=data.is_published,
            is_active=data.is_active,
        )

    async def update_branch(self, branch: Branch, data: BranchUpdate) -> Branch:
        patch = data.model_dump(exclude_unset=True)
        if "schedule" in patch and patch["schedule"] is not None:
            patch["schedule"] = [
                d if isinstance(d, dict) else d.model_dump() for d in patch["schedule"]
            ]
        for field, value in patch.items():
            setattr(branch, field, value)
        await branch.save()
        return branch

    async def update_branch_fields(self, branch: Branch, patch: dict) -> Branch:
        for field, value in patch.items():
            setattr(branch, field, value)
        await branch.save()
        return branch

    async def delete_branch(self, branch: Branch) -> None:
        await branch.delete()
