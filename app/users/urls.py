"""Auth-эндпоинты: login/me/refresh/logout (контракт раздел 6) + CRM users."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from app.common.schemas import LoginIn, PasswordReset, UserCreate, UserUpdate
from .service import *
from .repository import UserRepository


userRouter = APIRouter()
crmUsersRouter = APIRouter()
repo = UserRepository()
service = UserService(repo)

_refresh_scheme = HTTPBearer(auto_error=True)


@userRouter.post("/reg")
async def register(user: CreateUser):  # type: ignore
    """Внутренний эндпоинт создания пользователя (не из контракта).

    Полноценное управление пользователями (`/crm/users`) — следующий этап.
    """
    created = await service.register(user)
    return ok(created)


@userRouter.post("/login", summary="Login")
async def login(data: LoginIn):
    tokens = await service.login(data.login, data.password)
    return ok(tokens)


@userRouter.get("/me")
async def get_me(user: GetUser = Depends(get_current_user)):  # type: ignore
    return ok(await service.get_me(user))


@userRouter.post("/refresh")
async def refresh(creds: HTTPAuthorizationCredentials = Depends(_refresh_scheme)):
    tokens = await service.refresh(creds.credentials)
    return ok(tokens)


@userRouter.post("/logout")
async def logout(creds: HTTPAuthorizationCredentials = Depends(_refresh_scheme)):
    await service.logout(creds.credentials)
    return ok(None, "Вы вышли из системы")


# ── CRM: управление пользователями (/crm/users) ──────────────────────────────
# Доступ: супер-админ — все пользователи; владелец — сотрудники своих компаний.
@crmUsersRouter.get("/users")
async def list_users(
    page: PageParams = Depends(),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    items, total = await service.list_users(user, page.limit, page.offset, search, is_active)
    return paginated(items, total, page.limit, page.page)


@crmUsersRouter.post("/users", status_code=201)
async def create_user(
    data: UserCreate, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Создать пользователя (потом назначается сотрудником/владельцем)."""
    created = await service.create_user(user, data)
    return ok(created, "Пользователь создан")


@crmUsersRouter.get("/users/{user_id}")
async def get_user_detail(
    user_id: int, user: GetUser = Depends(get_current_user)  # type: ignore
):
    return ok(await service.get_user(user, user_id))


@crmUsersRouter.patch("/users/{user_id}")
async def update_user(
    user_id: int, data: UserUpdate, user: GetUser = Depends(get_current_user)  # type: ignore
):
    patch = data.model_dump(exclude_unset=True)
    return ok(await service.update_user(user, user_id, patch))


@crmUsersRouter.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int, data: PasswordReset, user: GetUser = Depends(get_current_user)  # type: ignore
):
    """Задать новый временный пароль (все refresh-токены отзываются)."""
    await service.reset_password(user, user_id, data.password)
    return ok(None, "Пароль обновлён")
