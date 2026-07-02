"""Доступ к данным: столы филиала."""
from typing import Optional

from app.models import Table


class TableRepository:
    async def list_tables(self, branch_id: int, limit: int, offset: int) -> tuple[list[Table], int]:
        qs = Table.filter(branch_id=branch_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def get_table(self, table_id: int) -> Optional[Table]:
        return await Table.filter(id=table_id).first()

    async def get_by_qr(self, qr_token: str) -> Optional[Table]:
        return await Table.filter(qr_token=qr_token, is_active=True).first()

    async def create_table(
        self,
        branch_id: int,
        number: str,
        zone: Optional[str],
        qr_token: str,
        title: Optional[str] = None,
        seats: Optional[int] = None,
        is_active: bool = True,
    ) -> Table:
        return await Table.create(
            branch_id=branch_id,
            title=title or number,
            number=number,
            zone=zone,
            seats=seats,
            qr_token=qr_token,
            is_active=is_active,
        )

    async def delete_table(self, table: Table) -> None:
        await table.delete()

    async def existing_numbers(self, branch_id: int) -> set[str]:
        rows = await Table.filter(branch_id=branch_id).values_list("number", flat=True)
        return set(rows)

    async def has_open_session(self, table_id: int) -> bool:
        from app.models import TableSession

        return await TableSession.filter(
            table_id=table_id, status=TableSession.OPEN
        ).exists()

    async def update_table(self, table, data) -> "Table":
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(table, field, value)
        await table.save()
        return table
