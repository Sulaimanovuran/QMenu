"""Бизнес-логика столов: создание с QR-токеном, удаление."""
from fastapi import HTTPException, status

from app.models import Table
from app.common.schemas import TableIn
from app.common.security import new_token
from .repository import TableRepository


class TableService:
    def __init__(self, repo: TableRepository):
        self.repo = repo

    async def list_tables(self, branch_id: int) -> list[Table]:
        return await self.repo.list_tables(branch_id)

    async def create_table(self, branch_id: int, data: TableIn) -> Table:
        return await self.repo.create_table(
            branch_id, data.number, data.zone, new_token()
        )

    async def delete_table(self, branch_id: int, table_id: int) -> None:
        table = await self.repo.get_table(table_id)
        if not table or table.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Стол не найден")
        await self.repo.delete_table(table)
