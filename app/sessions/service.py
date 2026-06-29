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
        table = await Table.filter(qr_token=data.qr_token, is_active=True).first()
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

        # первый в сессии становится хостом, остальные — pending
        if is_new_session:
            participant = await self.repo.create_participant(
                session.id, device_token, data.display_name, SessionParticipant.HOST
            )
            session.host_participant_id = participant.id
            await self.repo.save_session(session)
        else:
            participant = await self.repo.create_participant(
                session.id, device_token, data.display_name, SessionParticipant.PENDING
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
