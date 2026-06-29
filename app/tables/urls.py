"""Эндпоинты управления столами (персонал).

Table DTO отдаёт qr_token и public_url, чтобы фронт мог собрать QR-ссылку.
PUBLIC_BASE_URL берётся из настроек (для прод-домена), по умолчанию localhost.
"""
from fastapi import APIRouter, Depends

from app.common.schemas import TableIn, TableUpdate
from app.common.security import require_manage
from config import settings
from .service import TableService
from .repository import TableRepository

tableRouter = APIRouter()
service = TableService(TableRepository())
MANAGE = require_manage("admin", "manager")


def _serialize(t) -> dict:
    return {
        "id": t.id,
        "branch_id": t.branch_id,
        "number": t.number,
        "zone": t.zone,
        "qr_token": t.qr_token,
        "is_active": t.is_active,
        # фронт открывает гостевое меню по этой ссылке (qr_token внутри)
        "public_url": f"{settings.PUBLIC_BASE_URL}/t/{t.qr_token}",
    }


@tableRouter.get("/branches/{branch_id}/tables")
async def list_tables(branch_id: int, _=Depends(MANAGE)):
    tables = await service.list_tables(branch_id)
    return [_serialize(t) for t in tables]


@tableRouter.post("/branches/{branch_id}/tables", status_code=201)
async def create_table(branch_id: int, data: TableIn, _=Depends(MANAGE)):
    table = await service.create_table(branch_id, data)
    return _serialize(table)


@tableRouter.patch("/branches/{branch_id}/tables/{table_id}")
async def update_table(
    branch_id: int, table_id: int, data: TableUpdate, _=Depends(MANAGE)
):
    table = await service.update_table(branch_id, table_id, data)
    return _serialize(table)


@tableRouter.delete("/branches/{branch_id}/tables/{table_id}", status_code=204)
async def delete_table(branch_id: int, table_id: int, _=Depends(MANAGE)):
    await service.delete_table(branch_id, table_id)
