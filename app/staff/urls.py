"""Эндпоинты управления персоналом филиала."""
from fastapi import APIRouter, Depends

from app.common.schemas import EmployeeIn
from app.common.security import require_branch_owner
from .service import StaffService
from .repository import StaffRepository

staffRouter = APIRouter()
service = StaffService(StaffRepository())


def _serialize(emp) -> dict:
    return {
        "id": emp.id,
        "user": {"id": emp.user.id, "name": emp.user.name},
        "role": {"code": emp.role.code, "title": emp.role.title},
        "is_active": emp.is_active,
    }


@staffRouter.get("/branches/{branch_id}/employees")
async def list_employees(branch_id: int):
    emps = await service.list_employees(branch_id)
    return [_serialize(e) for e in emps]


@staffRouter.post("/branches/{branch_id}/employees", status_code=201)
async def add_employee(branch_id: int, data: EmployeeIn, _=Depends(require_branch_owner)):
    emp = await service.add_employee(branch_id, data)
    return _serialize(emp)


@staffRouter.delete("/branches/{branch_id}/employees/{employee_id}", status_code=204)
async def remove_employee(branch_id: int, employee_id: int, _=Depends(require_branch_owner)):
    await service.remove_employee(branch_id, employee_id)
