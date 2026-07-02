"""Бизнес-логика столов: создание с QR-токеном, bulk-создание, перевыпуск QR."""
from fastapi import HTTPException, status

from app.common.errors import AppError
from app.models import Table
from app.common.schemas import TableBulkIn, TableIn, TableUpdate
from app.common.security import new_token
from .repository import TableRepository


class TableService:
    def __init__(self, repo: TableRepository):
        self.repo = repo

    async def list_tables(self, branch_id: int, limit: int, offset: int) -> tuple[list[Table], int]:
        return await self.repo.list_tables(branch_id, limit, offset)

    async def create_table(self, branch_id: int, data: TableIn) -> Table:
        return await self.repo.create_table(
            branch_id, data.number, data.zone, new_token(),
            title=data.title, seats=data.seats, is_active=data.is_active,
        )

    async def bulk_create(self, branch_id: int, data: TableBulkIn) -> list[Table]:
        """Создать серию столов: prefix + номера from..to, каждому свой QR."""
        if data.to < data.from_:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "to должен быть >= from")
        if data.to - data.from_ + 1 > 100:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Не больше 100 столов за один запрос"
            )
        numbers = [
            f"{data.prefix}-{n}" if data.prefix else str(n)
            for n in range(data.from_, data.to + 1)
        ]
        existing = await self.repo.existing_numbers(branch_id)
        clash = sorted(set(numbers) & existing)
        if clash:
            raise AppError(
                status.HTTP_409_CONFLICT,
                "TABLE_NUMBER_TAKEN",
                f"Столы с номерами уже существуют: {', '.join(clash)}",
            )
        created = []
        for number in numbers:
            created.append(
                await self.repo.create_table(
                    branch_id, number, data.zone, new_token(),
                    title=number, seats=data.seats,
                )
            )
        return created

    async def regenerate_qr(self, branch_id: int, table_id: int) -> Table:
        table = await self._table_in_branch(branch_id, table_id)
        table.qr_token = new_token()
        await table.save()
        return table

    async def get_table(self, branch_id: int, table_id: int) -> Table:
        return await self._table_in_branch(branch_id, table_id)

    async def delete_table(self, branch_id: int, table_id: int) -> None:
        table = await self._table_in_branch(branch_id, table_id)
        if await self.repo.has_open_session(table_id):
            raise AppError(
                status.HTTP_409_CONFLICT,
                "TABLE_HAS_ACTIVE_SESSION",
                "Нельзя удалить стол с активной сессией — сначала закройте её",
            )
        await self.repo.delete_table(table)

    async def update_table(self, branch_id: int, table_id: int, data: TableUpdate):
        table = await self._table_in_branch(branch_id, table_id)
        return await self.repo.update_table(table, data)

    async def _table_in_branch(self, branch_id: int, table_id: int) -> Table:
        table = await self.repo.get_table(table_id)
        if not table or table.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Стол не найден")
        return table
