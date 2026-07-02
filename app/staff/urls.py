"""Эндпоинты управления персоналом филиала."""
from fastapi import APIRouter, Depends, Query

from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import EmployeeIn
from app.common.security import require_branch_owner
from app.models.users import GetUser
from app.users.service import get_current_user
from .service import StaffService
from .repository import StaffRepository

staffRouter = APIRouter()
service = StaffService(StaffRepository())


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


@staffRouter.delete("/branches/{branch_id}/employees/{employee_id}", status_code=204)
async def remove_employee(branch_id: int, employee_id: int, _=Depends(require_branch_owner)):
    await service.remove_employee(branch_id, employee_id)
