"""Гостевые эндпоинты сессий: скан QR, состояние, подтверждение участников.

Гость не авторизуется через JWT — он идентифицируется device_token,
который сервер выдаёт на первом скане и который клиент хранит у себя.
"""
from fastapi import APIRouter, Header
from typing import Optional

from app.common.responses import ok
from app.common.schemas import ScanIn, JoinDecision
from .service import SessionService
from .repository import SessionRepository

sessionRouter = APIRouter()
service = SessionService(SessionRepository())


@sessionRouter.post("/scan")
async def scan_qr(data: ScanIn):
    """Сканирование QR на столе. Открывает/присоединяет к сессии.

    Ответ содержит device_token — клиент обязан сохранить его и слать дальше
    в заголовке X-Device-Token.
    """
    return ok(await service.scan(data))


@sessionRouter.get("/{session_id}/state")
async def session_state(
    session_id: int, x_device_token: str = Header(...)
):
    """Поллинг состояния сессии гостем (подтвердили ли его, can_order и т.д.)."""
    return ok(await service.session_state(session_id, x_device_token))


@sessionRouter.get("/{session_id}/participants")
async def list_participants(session_id: int):
    """Список участников стола (для UI «кто за столом»)."""
    return ok(await service.list_participants(session_id))


@sessionRouter.post("/{session_id}/decide")
async def decide_join(
    session_id: int, data: JoinDecision, x_device_token: str = Header(...)
):
    """Хост подтверждает/отклоняет запрос участника на вступление."""
    return ok(await service.decide_join(session_id, x_device_token, data))


@sessionRouter.post("/{session_id}/close")
async def close_session(session_id: int, x_device_token: str = Header(...)):
    """Закрытие сессии (счёт оплачен). Доступно хосту; официант — отдельно."""
    return ok(await service.close_session(session_id, x_device_token))
