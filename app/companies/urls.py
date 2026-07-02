"""HTTP-эндпоинты: компании и филиалы. Доступ владельцу или супер-админу (JWT)."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Branch, GetCompany, GetBranch
from app.models.users import GetUser
from app.users.service import get_current_user
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import (
    BranchIn, BranchSettingsUpdate, BranchUpdate, CompanyIn, CompanyUpdate,
)
from app.common.security import require_manage
from .service import CompanyService
from .repository import CompanyRepository

companyRouter = APIRouter()
branchOpsRouter = APIRouter()   # /crm/branches/* (settings, my)
service = CompanyService(CompanyRepository())


# ── Компании ─────────────────────────────────────────────────────────────────
@companyRouter.get("/")
async def list_companies(
    page: PageParams = Depends(), user: GetUser = Depends(get_current_user)  # type: ignore
):
    items, total = await service.list_companies(user.id, user.is_superadmin, page.limit, page.offset)
    data = [await GetCompany.from_tortoise_orm(c) for c in items]
    return paginated(data, total, page.limit, page.page)


@companyRouter.post("/", status_code=201)
async def create_company(
    data: CompanyIn, user: GetUser = Depends(get_current_user)  # type: ignore
):
    company = await service.create_company(data, user.id)
    return ok(await GetCompany.from_tortoise_orm(company), "Компания создана")


@companyRouter.get("/{company_id}")
async def get_company(
    company_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    company = await service.get_owned_company(company_id, user.id, user.is_superadmin)
    return ok(await GetCompany.from_tortoise_orm(company))


@companyRouter.patch("/{company_id}")
async def update_company(
    company_id: int, data: CompanyUpdate, user: GetUser = Depends(get_current_user)  # type: ignore
):
    patch = data.model_dump(exclude_unset=True)
    company = await service.update_company(company_id, patch, user.id, user.is_superadmin)
    return ok(await GetCompany.from_tortoise_orm(company))


@companyRouter.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    await service.delete_company(company_id, user.id, user.is_superadmin)


# ── Филиалы ──────────────────────────────────────────────────────────────────
@companyRouter.get("/{company_id}/branches")
async def list_branches(
    company_id: int, page: PageParams = Depends(), user: GetUser = Depends(get_current_user)  # type: ignore
):
    items, total = await service.list_branches(
        company_id, user.id, user.is_superadmin, page.limit, page.offset
    )
    data = [await GetBranch.from_tortoise_orm(b) for b in items]
    return paginated(data, total, page.limit, page.page)


@companyRouter.post("/{company_id}/branches", status_code=201)
async def create_branch(
    company_id: int, data: BranchIn, user: GetUser = Depends(get_current_user)  # type: ignore
):
    branch = await service.create_branch(company_id, data, user.id, user.is_superadmin)
    return ok(await GetBranch.from_tortoise_orm(branch), "Филиал создан")


@companyRouter.patch("/{company_id}/branches/{branch_id}")
async def update_branch(
    company_id: int,
    branch_id: int,
    data: BranchUpdate,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    branch = await service.update_branch(company_id, branch_id, data, user.id, user.is_superadmin)
    return ok(await GetBranch.from_tortoise_orm(branch))


@companyRouter.delete("/{company_id}/branches/{branch_id}", status_code=204)
async def delete_branch(
    company_id: int, branch_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    await service.delete_branch(company_id, branch_id, user.id, user.is_superadmin)


# ── Настройки филиала (/crm/branches/{branch_id}/settings) ───────────────────
def _settings_dict(branch: Branch) -> dict:
    return {
        "branch_id": branch.id,
        "moderation_mode": branch.moderation_mode,
        "allow_guest_join_without_host": branch.allow_guest_join_without_host,
        "allow_order_without_approval": branch.allow_order_without_approval,
        "is_active": branch.is_active,
        "is_published": branch.is_published,
    }


@branchOpsRouter.get("/branches/{branch_id}/settings")
async def get_branch_settings(branch_id: int, _=Depends(require_manage("branch_admin"))):
    """Настройки филиала, влияющие на guest/order flow."""
    branch = await Branch.filter(id=branch_id).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
    return ok(_settings_dict(branch))


@branchOpsRouter.patch("/branches/{branch_id}/settings")
async def update_branch_settings(
    branch_id: int, data: BranchSettingsUpdate, _=Depends(require_manage("branch_admin"))
):
    branch = await Branch.filter(id=branch_id).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)
    await branch.save()
    return ok(_settings_dict(branch), "Настройки обновлены")
