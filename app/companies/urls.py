"""HTTP-эндпоинты: компании и филиалы. Доступ владельцу или супер-админу (JWT)."""
from fastapi import APIRouter, Depends

from app.models import GetCompany, GetBranch
from app.models.users import GetUser
from app.users.service import get_current_user
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import CompanyIn, BranchIn, BranchUpdate
from .service import CompanyService
from .repository import CompanyRepository

companyRouter = APIRouter()
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
