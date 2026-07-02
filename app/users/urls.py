"""Auth-эндпоинты: login/me/refresh/logout (контракт раздел 6) + внутренняя reg."""
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.responses import ok
from app.common.schemas import LoginIn
from .service import *
from .repository import UserRepository


userRouter = APIRouter()
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
