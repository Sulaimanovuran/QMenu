"""Эндпоинты управления столами (персонал)."""
from fastapi import APIRouter, Depends

from app.models import GetTable
from app.common.schemas import TableIn
from app.common.security import require_manage
from .service import TableService
from .repository import TableRepository

tableRouter = APIRouter()
service = TableService(TableRepository())
MANAGE = require_manage("admin", "manager")


@tableRouter.get("/branches/{branch_id}/tables", response_model=list[GetTable])
async def list_tables(branch_id: int):
    return await service.list_tables(branch_id)


@tableRouter.post(
    "/branches/{branch_id}/tables", response_model=GetTable, status_code=201
)
async def create_table(branch_id: int, data: TableIn, _=Depends(MANAGE)):
    table = await service.create_table(branch_id, data)
    return await GetTable.from_tortoise_orm(table)


@tableRouter.delete("/branches/{branch_id}/tables/{table_id}", status_code=204)
async def delete_table(branch_id: int, table_id: int, _=Depends(MANAGE)):
    await service.delete_table(branch_id, table_id)
