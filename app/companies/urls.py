"""HTTP-эндпоинты: компании и филиалы. Доступ только владельцу (JWT)."""
from fastapi import APIRouter, Depends

from app.models import GetCompany, GetBranch
from app.models.users import GetUser
from app.users.service import get_current_user
from app.common.schemas import CompanyIn, BranchIn, BranchUpdate
from .service import CompanyService
from .repository import CompanyRepository

companyRouter = APIRouter()
service = CompanyService(CompanyRepository())


# ── Компании ─────────────────────────────────────────────────────────────────
@companyRouter.get("/", response_model=list[GetCompany])
async def list_companies(user: GetUser = Depends(get_current_user)):  # type: ignore
    return await service.list_companies(user.id)


@companyRouter.post("/", response_model=GetCompany, status_code=201)
async def create_company(
    data: CompanyIn, user: GetUser = Depends(get_current_user)  # type: ignore
):
    company = await service.create_company(data, user.id)
    return await GetCompany.from_tortoise_orm(company)


@companyRouter.get("/{company_id}", response_model=GetCompany)
async def get_company(
    company_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    company = await service.get_owned_company(company_id, user.id)
    return await GetCompany.from_tortoise_orm(company)


@companyRouter.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    await service.delete_company(company_id, user.id)


# ── Филиалы ──────────────────────────────────────────────────────────────────
@companyRouter.get("/{company_id}/branches", response_model=list[GetBranch])
async def list_branches(
    company_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    return await service.list_branches(company_id, user.id)


@companyRouter.post(
    "/{company_id}/branches", response_model=GetBranch, status_code=201
)
async def create_branch(
    company_id: int, data: BranchIn, user: GetUser = Depends(get_current_user)  # type: ignore
):
    branch = await service.create_branch(company_id, data, user.id)
    return await GetBranch.from_tortoise_orm(branch)


@companyRouter.patch(
    "/{company_id}/branches/{branch_id}", response_model=GetBranch
)
async def update_branch(
    company_id: int,
    branch_id: int,
    data: BranchUpdate,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    branch = await service.update_branch(company_id, branch_id, data, user.id)
    return await GetBranch.from_tortoise_orm(branch)


@companyRouter.delete(
    "/{company_id}/branches/{branch_id}", status_code=204
)
async def delete_branch(
    company_id: int, branch_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    await service.delete_branch(company_id, branch_id, user.id)
