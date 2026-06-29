"""Доступ к данным: столы филиала."""
from typing import Optional

from app.models import Table


class TableRepository:
    async def list_tables(self, branch_id: int) -> list[Table]:
        return await Table.filter(branch_id=branch_id).all()

    async def get_table(self, table_id: int) -> Optional[Table]:
        return await Table.filter(id=table_id).first()

    async def get_by_qr(self, qr_token: str) -> Optional[Table]:
        return await Table.filter(qr_token=qr_token, is_active=True).first()

    async def create_table(
        self, branch_id: int, number: str, zone: Optional[str], qr_token: str
    ) -> Table:
        return await Table.create(
            branch_id=branch_id, number=number, zone=zone, qr_token=qr_token
        )

    async def delete_table(self, table: Table) -> None:
        await table.delete()

    async def update_table(self, table, data) -> "Table":
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(table, field, value)
        await table.save()
        return table
