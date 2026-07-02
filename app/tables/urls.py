"""Эндпоинты управления столами (персонал, CRM).

Table DTO отдаёт qr_token и public_url, чтобы фронт мог собрать QR-ссылку.
PUBLIC_BASE_URL берётся из настроек (для прод-домена), по умолчанию localhost.
"""
from fastapi import APIRouter, Depends

from app.common.schemas import TableBulkIn, TableIn, TableUpdate
from app.common.security import require_manage
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from config import settings
from .service import TableService
from .repository import TableRepository

tableRouter = APIRouter()
service = TableService(TableRepository())
MANAGE = require_manage("branch_admin")


def _serialize(t) -> dict:
    return {
        "id": t.id,
        "branch_id": t.branch_id,
        "title": t.title,
        "number": t.number,
        "zone": t.zone,
        "seats": t.seats,
        "qr_token": t.qr_token,
        "is_active": t.is_active,
        # фронт открывает гостевое меню по этой ссылке (qr_token внутри)
        "public_url": f"{settings.PUBLIC_BASE_URL}/t/{t.qr_token}",
    }


@tableRouter.get("/branches/{branch_id}/tables")
async def list_tables(branch_id: int, page: PageParams = Depends(), _=Depends(MANAGE)):
    tables, total = await service.list_tables(branch_id, page.limit, page.offset)
    return paginated([_serialize(t) for t in tables], total, page.limit, page.page)


@tableRouter.post("/branches/{branch_id}/tables", status_code=201)
async def create_table(branch_id: int, data: TableIn, _=Depends(MANAGE)):
    table = await service.create_table(branch_id, data)
    return ok(_serialize(table), "Стол создан")


@tableRouter.patch("/branches/{branch_id}/tables/{table_id}")
async def update_table(
    branch_id: int, table_id: int, data: TableUpdate, _=Depends(MANAGE)
):
    table = await service.update_table(branch_id, table_id, data)
    return ok(_serialize(table))


@tableRouter.delete("/branches/{branch_id}/tables/{table_id}", status_code=204)
async def delete_table(branch_id: int, table_id: int, _=Depends(MANAGE)):
    await service.delete_table(branch_id, table_id)


@tableRouter.get("/branches/{branch_id}/tables/{table_id}")
async def get_table(branch_id: int, table_id: int, _=Depends(MANAGE)):
    table = await service.get_table(branch_id, table_id)
    return ok(_serialize(table))


@tableRouter.post("/branches/{branch_id}/tables/bulk", status_code=201)
async def bulk_create_tables(branch_id: int, data: TableBulkIn, _=Depends(MANAGE)):
    """Создать серию столов (prefix + from..to), каждому — свой QR."""
    tables = await service.bulk_create(branch_id, data)
    return ok([_serialize(t) for t in tables], f"Создано столов: {len(tables)}")


@tableRouter.post("/branches/{branch_id}/tables/{table_id}/regenerate-qr")
async def regenerate_qr(branch_id: int, table_id: int, _=Depends(MANAGE)):
    """Перевыпустить QR-токен стола (старая ссылка перестаёт работать)."""
    table = await service.regenerate_qr(branch_id, table_id)
    return ok(
        {
            "qr_token": table.qr_token,
            "public_url": f"{settings.PUBLIC_BASE_URL}/t/{table.qr_token}",
        },
        "QR обновлён",
    )


@tableRouter.get("/branches/{branch_id}/tables/{table_id}/qr")
async def table_qr(branch_id: int, table_id: int, _=Depends(MANAGE)):
    """QR-данные стола для печати (фронт сам рисует QR по public_url)."""
    table = await service.get_table(branch_id, table_id)
    return ok(
        {
            "table_title": table.title or table.number,
            "qr_token": table.qr_token,
            "public_url": f"{settings.PUBLIC_BASE_URL}/t/{table.qr_token}",
        }
    )
