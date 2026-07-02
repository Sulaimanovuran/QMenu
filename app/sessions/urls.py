"""Эндпоинты сессий: гостевой контур (device_token) + CRM-контур (JWT).

Гость не авторизуется через JWT — он идентифицируется device_token,
который сервер выдаёт на первом скане и который клиент хранит у себя.
"""
from fastapi import APIRouter, Depends, Header, Query
from typing import Optional

from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import JoinDecision, ParticipantDecide, ParticipantRename, ScanIn
from app.common.security import check_branch_access, require_manage
from app.models.users import GetUser
from app.users.service import get_current_user
from .service import SessionService
from .repository import SessionRepository

sessionRouter = APIRouter()
crm_session_router = APIRouter()
service = SessionService(SessionRepository())

# роли CRM-контура сессий: владелец/супер-админ проходят внутри require_manage
CRM_ROLES = ("branch_admin", "waiter")
MANAGE_SESSIONS = require_manage(*CRM_ROLES)


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


@sessionRouter.patch("/{session_id}/participants/me")
async def rename_me(
    session_id: int, data: ParticipantRename, x_device_token: str = Header(...)
):
    """Гость меняет своё имя (отображается в участниках и заказах)."""
    return ok(await service.rename_me(session_id, x_device_token, data.name))


@sessionRouter.post("/{session_id}/participants/me/leave")
async def leave_session(session_id: int, x_device_token: str = Header(...)):
    """Гость выходит из сессии (хосту запрещено — он закрывает сессию)."""
    return ok(await service.leave_me(session_id, x_device_token), "Вы вышли из сессии")


# ── CRM: сессии столов ────────────────────────────────────────────────────────
@crm_session_router.get("/branches/{branch_id}/sessions")
async def crm_list_sessions(
    branch_id: int,
    page: PageParams = Depends(),
    status: Optional[str] = Query(None, pattern="^(open|closed)$"),
    table_id: Optional[int] = Query(None),
    _=Depends(MANAGE_SESSIONS),
):
    """Активные и завершённые сессии столов филиала."""
    items, total = await service.crm_list_sessions(
        branch_id, page.limit, page.offset, status, table_id
    )
    return paginated(items, total, page.limit, page.page)


@crm_session_router.get("/sessions/{session_id}")
async def crm_session_detail(
    session_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Деталка сессии: участники и заказы."""
    data, branch_id = await service.crm_session_detail(session_id)
    await check_branch_access(branch_id, user, *CRM_ROLES)
    return ok(data)


@crm_session_router.post("/sessions/{session_id}/close")
async def crm_close_session(
    session_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Закрыть сессию стола администратором (если хост ушёл, счёт оплачен)."""
    # доступ проверяем до изменения состояния
    detail, branch_id = await service.crm_session_detail(session_id)
    await check_branch_access(branch_id, user, *CRM_ROLES)
    data, _ = await service.crm_close_session(session_id)
    return ok(data, "Сессия закрыта")


@crm_session_router.get("/sessions/{session_id}/participants")
async def crm_participants(
    session_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    data, branch_id = await service.crm_participants(session_id)
    await check_branch_access(branch_id, user, *CRM_ROLES)
    return ok(data)


@crm_session_router.post("/sessions/{session_id}/participants/{participant_id}/decide")
async def crm_decide_participant(
    session_id: int,
    participant_id: int,
    data: ParticipantDecide,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    """CRM подтверждает/отклоняет участника, если хост не отвечает."""
    # сначала только читаем сессию для проверки доступа
    _, branch_id = await service.crm_participants(session_id)
    await check_branch_access(branch_id, user, *CRM_ROLES)
    result, _ = await service.crm_decide(session_id, participant_id, data.decision)
    return ok(result)
