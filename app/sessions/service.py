"""Логика сессий стола в стиле mCafe.

Сценарий:
1. Первый гость сканирует QR -> создаётся сессия + участник со статусом host.
2. Следующие гости сканируют тот же QR -> участник pending, хост получает запрос.
3. Хост подтверждает/отклоняет -> participant approved/rejected.
4. Заказы могут делать только участники со статусом host или approved.

Гость идентифицируется анонимным device_token (cookie/localStorage у клиента).
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models import Table, TableSession, SessionParticipant
from app.common.schemas import ScanIn, JoinDecision
from app.common.security import new_token
from .repository import SessionRepository


class SessionService:
    def __init__(self, repo: SessionRepository):
        self.repo = repo

    async def scan(self, data: ScanIn) -> dict:
        """Гость сканирует QR. Возвращает состояние участника и его device_token."""
        table = (
            await Table.filter(qr_token=data.qr_token, is_active=True)
            .prefetch_related("branch")
            .first()
        )
        if not table:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Стол не найден")

        # выдаём токен устройства, если у гостя его ещё нет
        device_token = data.device_token or new_token()

        # активная сессия стола или новая
        session = await self.repo.open_session(table.id)
        is_new_session = session is None
        if is_new_session:
            session = await self.repo.create_session(table.id)

        # участник уже есть для этого устройства?
        participant = await self.repo.get_participant_by_device(
            session.id, device_token
        )
        if participant:
            return self._state(session, participant, device_token)

        # первый в сессии становится хостом; остальные — pending, либо сразу
        # approved, если филиал разрешает вход без подтверждения хостом
        if is_new_session:
            participant = await self.repo.create_participant(
                session.id, device_token, data.display_name, SessionParticipant.HOST
            )
            session.host_participant_id = participant.id
            await self.repo.save_session(session)
        else:
            join_status = (
                SessionParticipant.APPROVED
                if table.branch.allow_guest_join_without_host
                else SessionParticipant.PENDING
            )
            participant = await self.repo.create_participant(
                session.id, device_token, data.display_name, join_status
            )

        return self._state(session, participant, device_token)

    async def session_state(self, session_id: int, device_token: str) -> dict:
        """Текущее состояние сессии для конкретного устройства (поллинг гостя)."""
        session = await self._get_open_or_any(session_id)
        participant = await self.repo.get_participant_by_device(
            session_id, device_token
        )
        if not participant:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этой сессии")
        return self._state(session, participant, device_token)

    async def list_participants(self, session_id: int) -> list[dict]:
        parts = await self.repo.list_participants(session_id)
        return [self._participant_dict(p) for p in parts]

    async def decide_join(self, session_id: int, device_token: str, data: JoinDecision) -> dict:
        """Хост подтверждает/отклоняет участника."""
        session = await self._get_open(session_id)
        host = await self._require_host(session_id, device_token)

        target = await self.repo.get_participant(data.participant_id)
        if not target or target.session_id != session_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")
        if target.id == host.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя изменить хоста")

        target.status = (
            SessionParticipant.APPROVED if data.approve else SessionParticipant.REJECTED
        )
        await self.repo.save_participant(target)
        return self._participant_dict(target)

    async def close_session(self, session_id: int, device_token: str) -> dict:
        """Закрытие сессии хостом (счёт оплачен). Новые заказы запрещены."""
        session = await self._get_open(session_id)
        await self._require_host(session_id, device_token)
        session.status = TableSession.CLOSED
        session.closed_at = datetime.now(timezone.utc)
        await self.repo.save_session(session)
        return {"id": session.id, "status": session.status}

    async def rename_me(self, session_id: int, device_token: str, name: str) -> dict:
        """Гость меняет своё отображаемое имя."""
        await self._get_open(session_id)
        me = await self.repo.get_participant_by_device(session_id, device_token)
        if not me:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этой сессии")
        me.display_name = name
        await self.repo.save_participant(me)
        return self._participant_dict(me)

    async def leave_me(self, session_id: int, device_token: str) -> dict:
        """Гость выходит из сессии. Хосту выход запрещён (базовое правило)."""
        await self._get_open(session_id)
        me = await self.repo.get_participant_by_device(session_id, device_token)
        if not me:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этой сессии")
        if me.status == SessionParticipant.HOST:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Хост не может покинуть сессию — сначала закройте её",
            )
        me.status = SessionParticipant.LEFT
        await self.repo.save_participant(me)
        return self._participant_dict(me)

    # ── CRM ──────────────────────────────────────────────────────────────────
    async def crm_list_sessions(
        self, branch_id: int, limit: int, offset: int,
        status_filter=None, table_id=None,
    ) -> tuple[list[dict], int]:
        sessions, total = await self.repo.list_branch_sessions(
            branch_id, limit, offset, status_filter, table_id
        )
        return [self._session_dict(s) for s in sessions], total

    async def crm_session_detail(self, session_id: int) -> tuple[dict, int]:
        """Деталка сессии для CRM + branch_id для проверки доступа в urls."""
        session = await self.repo.get_session_full(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        branch_id = session.table.branch_id
        data = self._session_dict(session)
        data["participants"] = [self._participant_dict(p) for p in session.participants]
        data["orders"] = [
            {
                "id": o.id,
                "status": o.status,
                "total_minor": o.total_minor,
                "participant_id": o.participant_id,
                "participant_name": o.participant.display_name if o.participant else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "items_count": len(o.items),
            }
            for o in session.orders
        ]
        return data, branch_id

    async def crm_close_session(self, session_id: int) -> tuple[dict, int]:
        session = await self.repo.get_session_full(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        branch_id = session.table.branch_id
        if session.status != TableSession.OPEN:
            raise HTTPException(status.HTTP_409_CONFLICT, "Сессия уже закрыта")
        session.status = TableSession.CLOSED
        session.closed_at = datetime.now(timezone.utc)
        await self.repo.save_session(session)
        return {"id": session.id, "status": session.status}, branch_id

    async def crm_participants(self, session_id: int) -> tuple[list[dict], int]:
        session = await self.repo.get_session_full(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        return [self._participant_dict(p) for p in session.participants], session.table.branch_id

    async def crm_decide(
        self, session_id: int, participant_id: int, decision: str
    ) -> tuple[dict, int]:
        """CRM подтверждает/отклоняет участника (если хост не отвечает)."""
        session = await self.repo.get_session_full(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        branch_id = session.table.branch_id
        target = await self.repo.get_participant(participant_id)
        if not target or target.session_id != session_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")
        if target.status == SessionParticipant.HOST:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя изменить хоста")
        target.status = decision
        await self.repo.save_participant(target)
        return self._participant_dict(target), branch_id

    def _session_dict(self, s: TableSession) -> dict:
        table = getattr(s, "table", None)
        return {
            "id": s.id,
            "status": s.status,
            "table_id": s.table_id,
            "table_title": (table.title or table.number) if table else None,
            "table_zone": table.zone if table else None,
            "host_participant_id": s.host_participant_id,
            "opened_at": s.opened_at.isoformat() if s.opened_at else None,
            "closed_at": s.closed_at.isoformat() if s.closed_at else None,
        }

    # ── helpers ──────────────────────────────────────────────────────────────
    async def _get_open(self, session_id: int) -> TableSession:
        session = await self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        if session.status != TableSession.OPEN:
            raise HTTPException(status.HTTP_409_CONFLICT, "Сессия уже закрыта")
        return session

    async def _get_open_or_any(self, session_id: int) -> TableSession:
        session = await self.repo.get_session(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
        return session

    async def _require_host(self, session_id: int, device_token: str) -> SessionParticipant:
        me = await self.repo.get_participant_by_device(session_id, device_token)
        if not me or me.status != SessionParticipant.HOST:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Только хост может подтверждать участников"
            )
        return me

    def _state(self, session, participant, device_token: str) -> dict:
        return {
            "device_token": device_token,
            "session": {"id": session.id, "status": session.status},
            "participant": self._participant_dict(participant),
            "can_order": participant.status in SessionParticipant.CAN_ORDER,
            "is_host": participant.status == SessionParticipant.HOST,
        }

    def _participant_dict(self, p: SessionParticipant) -> dict:
        return {
            "id": p.id,
            "display_name": p.display_name,
            "status": p.status,
        }
