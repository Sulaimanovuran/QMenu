"""Эндпоинты управления персоналом филиала и компании."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import CompanyEmployeeIn, EmployeeIn, EmployeeUpdate
from app.common.security import require_branch_owner
from app.models import Company
from app.models.users import GetUser
from app.users.service import get_current_user
from .service import StaffService
from .repository import StaffRepository

staffRouter = APIRouter()
service = StaffService(StaffRepository())


async def _require_company_owner(company_id: int, user) -> Company:
    """Супер-админ или владелец компании (для company-level employees)."""
    company = await Company.filter(id=company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Компания не найдена")
    if not user.is_superadmin and company.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Доступно только владельцу компании")
    return company


@staffRouter.get("/me/branches")
async def my_branches(user: GetUser = Depends(get_current_user)):  # type: ignore
    """Филиалы, доступные текущему сотруднику (после логина — куда заходить)."""
    return ok(await service.my_branches(user.id))


@staffRouter.get("/users/search")
async def search_users(
    query: str = Query(..., min_length=1),
    _: GetUser = Depends(get_current_user),  # type: ignore
):
    """Поиск пользователей по логину/имени (для выбора сотрудника в CRM вместо ввода ID)."""
    return ok(await service.search_users(query))


def _serialize(emp) -> dict:
    return {
        "id": emp.id,
        "user": {"id": emp.user.id, "login": emp.user.login, "full_name": emp.user.full_name},
        "role": {"code": emp.role.code, "title": emp.role.title},
        "company_id": emp.company_id,
        "branch_id": emp.branch_id,
        "status": emp.status,
        "is_active": emp.is_active,
    }


@staffRouter.get("/branches/{branch_id}/employees")
async def list_employees(branch_id: int, page: PageParams = Depends(), _=Depends(require_branch_owner)):
    emps, total = await service.list_employees(branch_id, page.limit, page.offset)
    return paginated([_serialize(e) for e in emps], total, page.limit, page.page)


@staffRouter.post("/branches/{branch_id}/employees", status_code=201)
async def add_employee(branch_id: int, data: EmployeeIn, _=Depends(require_branch_owner)):
    emp = await service.add_employee(branch_id, data)
    return ok(_serialize(emp), "Сотрудник добавлен")


@staffRouter.patch("/branches/{branch_id}/employees/{employee_id}")
async def update_employee(
    branch_id: int, employee_id: int, data: EmployeeUpdate, _=Depends(require_branch_owner)
):
    """Сменить роль сотрудника или заблокировать/разблокировать его."""
    emp = await service.update_employee(branch_id, employee_id, data)
    return ok(_serialize(emp))


@staffRouter.delete("/branches/{branch_id}/employees/{employee_id}", status_code=204)
async def remove_employee(branch_id: int, employee_id: int, _=Depends(require_branch_owner)):
    await service.remove_employee(branch_id, employee_id)


@staffRouter.get("/employees/{employee_id}")
async def employee_detail(
    employee_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Деталка назначения сотрудника (супер-админ или владелец компании)."""
    emp = await service.employee_detail(employee_id)
    await _require_company_owner(emp.company_id, user)
    return ok(_serialize(emp))


# ── Сотрудники уровня компании (роль owner и т.п., branch=None) ───────────────
@staffRouter.get("/companies/{company_id}/employees")
async def list_company_employees(
    company_id: int,
    page: PageParams = Depends(),
    branch_id: Optional[int] = Query(None),
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    """Все сотрудники компании (по всем филиалам и уровня компании)."""
    await _require_company_owner(company_id, user)
    emps, total = await service.list_company_employees(
        company_id, page.limit, page.offset, branch_id
    )
    return paginated([_serialize(e) for e in emps], total, page.limit, page.page)


@staffRouter.post("/companies/{company_id}/employees", status_code=201)
async def add_company_employee(
    company_id: int,
    data: CompanyEmployeeIn,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    """Назначить пользователя на роль уровня компании (owner — только супер-админ)."""
    await _require_company_owner(company_id, user)
    emp = await service.add_company_employee(company_id, data, user.is_superadmin)
    return ok(_serialize(emp), "Роль назначена")


@staffRouter.delete("/companies/{company_id}/employees/{employee_id}", status_code=204)
async def remove_company_employee(
    company_id: int,
    employee_id: int,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    await _require_company_owner(company_id, user)
    await service.remove_company_employee(company_id, employee_id)
