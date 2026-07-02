"""Доступ к данным: сессии столов и участники."""
from typing import Optional

from app.models import TableSession, SessionParticipant


class SessionRepository:
    async def open_session(self, table_id: int) -> Optional[TableSession]:
        """Активная (open) сессия стола, если есть."""
        return await TableSession.filter(
            table_id=table_id, status=TableSession.OPEN
        ).first()

    async def create_session(self, table_id: int) -> TableSession:
        return await TableSession.create(table_id=table_id)

    async def get_session(self, session_id: int) -> Optional[TableSession]:
        return await TableSession.filter(id=session_id).first()

    async def save_session(self, session: TableSession) -> None:
        await session.save()

    async def get_participant_by_device(
        self, session_id: int, device_token: str
    ) -> Optional[SessionParticipant]:
        return await SessionParticipant.filter(
            session_id=session_id, device_token=device_token
        ).first()

    async def get_participant(self, participant_id: int) -> Optional[SessionParticipant]:
        return await SessionParticipant.filter(id=participant_id).first()

    async def create_participant(
        self, session_id: int, device_token: str, display_name: Optional[str], status: str
    ) -> SessionParticipant:
        return await SessionParticipant.create(
            session_id=session_id,
            device_token=device_token,
            display_name=display_name,
            status=status,
        )

    async def save_participant(self, p: SessionParticipant) -> None:
        await p.save()

    async def list_participants(self, session_id: int) -> list[SessionParticipant]:
        return await SessionParticipant.filter(session_id=session_id).all()

    async def pending_participants(self, session_id: int) -> list[SessionParticipant]:
        return await SessionParticipant.filter(
            session_id=session_id, status=SessionParticipant.PENDING
        ).all()

    # ── CRM ──────────────────────────────────────────────────────────────────
    async def list_branch_sessions(
        self,
        branch_id: int,
        limit: int,
        offset: int,
        status: Optional[str] = None,
        table_id: Optional[int] = None,
    ) -> tuple[list[TableSession], int]:
        qs = TableSession.filter(table__branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        if table_id is not None:
            qs = qs.filter(table_id=table_id)
        total = await qs.count()
        items = (
            await qs.prefetch_related("table")
            .order_by("-opened_at")
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    async def get_session_full(self, session_id: int) -> Optional[TableSession]:
        """Сессия с цепочкой до филиала, участниками и заказами (CRM-деталка)."""
        return (
            await TableSession.filter(id=session_id)
            .prefetch_related("table__branch", "participants", "orders__items", "orders__participant")
            .first()
        )
