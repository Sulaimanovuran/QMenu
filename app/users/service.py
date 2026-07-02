import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config.settings import SECRET_KEY, ACCESS_TOKEN_TTL_MINUTES, REFRESH_TOKEN_TTL_DAYS
from app.common.errors import AppError
from app.common.roles import PERMISSIONS_BY_ROLE
from app.models import Company, Employee, RefreshToken

from .repository import UserRepository
from app.models.users import User, GetUser, CreateUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def authenticate_user(login: str, password: str):
    user = await User.get_or_none(login=login)
    if not user or not user.is_active:
        return None
    if not user.verify_password(password):
        return None
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
        )
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный токен")
    user = await User.filter(id=payload.get('id')).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
        )
    return await GetUser.from_tortoise_orm(user)


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, user: CreateUser):  # type: ignore
        return await self.repo.create(user)

    async def create_admin(self):
        if await User.get_or_none(login="admin"):
            return
        await self.repo.create_admin(
            login="admin",
            full_name="Администратор",
            password="admin",
        )

    def _issue_access_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "id": user.id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    async def _issue_refresh_token(self, user: User) -> str:
        from app.common.security import new_token  # локальный импорт: избегаем цикла security<->users.service

        raw_token = new_token()
        await RefreshToken.create(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        )
        return raw_token

    async def login(self, login: str, password: str) -> dict:
        user = await authenticate_user(login, password)
        if not user:
            raise AppError(
                status.HTTP_401_UNAUTHORIZED,
                "INVALID_CREDENTIALS",
                "Неверный логин или пароль",
            )
        return {
            "access_token": self._issue_access_token(user),
            "refresh_token": await self._issue_refresh_token(user),
        }

    async def refresh(self, raw_refresh_token: str) -> dict:
        token_row = (
            await RefreshToken.filter(token_hash=_hash_token(raw_refresh_token), revoked=False)
            .prefetch_related("user")
            .first()
        )
        now = datetime.now(timezone.utc)
        if not token_row or token_row.expires_at.replace(tzinfo=timezone.utc) < now:
            raise AppError(
                status.HTTP_401_UNAUTHORIZED,
                "INVALID_CREDENTIALS",
                "Refresh-токен недействителен, войдите заново",
            )
        token_row.revoked = True
        await token_row.save()
        user = token_row.user
        return {
            "access_token": self._issue_access_token(user),
            "refresh_token": await self._issue_refresh_token(user),
        }

    async def logout(self, raw_refresh_token: str) -> None:
        await RefreshToken.filter(token_hash=_hash_token(raw_refresh_token)).update(revoked=True)

    # ── CRM: управление пользователями ───────────────────────────────────────
    async def _scope_user_ids(self, actor) -> Optional[set[int]]:
        """Каких пользователей видит actor. None = всех (супер-админ).

        Владелец видит сотрудников своих компаний и самого себя.
        Иначе — 403.
        """
        if actor.is_superadmin:
            return None
        owned = await Company.filter(owner_id=actor.id).values_list("id", flat=True)
        if not owned:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        emp_user_ids = await Employee.filter(company_id__in=list(owned)).values_list(
            "user_id", flat=True
        )
        return set(emp_user_ids) | {actor.id}

    def _user_dict(self, u: User) -> dict:
        return {
            "id": u.id,
            "login": u.login,
            "full_name": u.full_name,
            "phone": u.phone,
            "is_active": u.is_active,
        }

    async def list_users(
        self, actor, limit: int, offset: int,
        search: Optional[str] = None, is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        from tortoise.expressions import Q

        scope = await self._scope_user_ids(actor)
        qs = User.all()
        if scope is not None:
            qs = qs.filter(id__in=list(scope))
        if search:
            qs = qs.filter(Q(login__icontains=search) | Q(full_name__icontains=search))
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        total = await qs.count()
        users = await qs.offset(offset).limit(limit).all()
        return [self._user_dict(u) for u in users], total

    async def create_user(self, actor, data) -> dict:
        # создавать пользователей может супер-админ или владелец компании
        if not actor.is_superadmin:
            if not await Company.filter(owner_id=actor.id).exists():
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        if await User.get_or_none(login=data.login):
            raise AppError(
                status.HTTP_409_CONFLICT, "LOGIN_TAKEN",
                "Проверьте поля формы",
                {"login": ["Логин уже занят"]},
            )
        user = User(
            login=data.login, full_name=data.full_name,
            phone=data.phone, is_active=data.is_active,
        )
        user.set_password(data.password)
        await user.save()
        return self._user_dict(user)

    async def _scoped_user(self, actor, user_id: int) -> User:
        scope = await self._scope_user_ids(actor)
        if scope is not None and user_id not in scope:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
        user = await User.get_or_none(id=user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
        return user

    async def get_user(self, actor, user_id: int) -> dict:
        return self._user_dict(await self._scoped_user(actor, user_id))

    async def update_user(self, actor, user_id: int, patch: dict) -> dict:
        user = await self._scoped_user(actor, user_id)
        for field, value in patch.items():
            setattr(user, field, value)
        await user.save()
        return self._user_dict(user)

    async def reset_password(self, actor, user_id: int, password: str) -> None:
        user = await self._scoped_user(actor, user_id)
        user.set_password(password)
        await user.save()
        # все refresh-токены пользователя перестают действовать
        await RefreshToken.filter(user_id=user_id).update(revoked=True)

    async def get_me(self, user: GetUser) -> dict:  # type: ignore
        if user.is_superadmin:
            role = "super_admin"
        else:
            owned = await Company.filter(owner_id=user.id).exists()
            employees = (
                await Employee.filter(user_id=user.id, is_active=True)
                .prefetch_related("role")
                .all()
            )
            employee_roles = {e.role.code for e in employees}
            if owned:
                role = "owner"
            elif "branch_admin" in employee_roles:
                role = "branch_admin"
            elif "waiter" in employee_roles:
                role = "waiter"
            elif "kitchen" in employee_roles:
                role = "kitchen"
            else:
                role = employee_roles.pop() if employee_roles else "owner"

        roles = {role}
        company_ids: list[int] = []
        branch_ids: list[int] = []
        if not user.is_superadmin:
            company_ids = [c.id for c in await Company.filter(owner_id=user.id).all()]
            if company_ids:
                roles.add("owner")
            employees = (
                await Employee.filter(user_id=user.id, is_active=True)
                .prefetch_related("role")
                .all()
            )
            branch_ids = sorted({e.branch_id for e in employees})
            roles |= {e.role.code for e in employees}

        permissions: set[str] = set()
        for r in roles:
            permissions |= set(PERMISSIONS_BY_ROLE.get(r, []))

        return {
            "id": user.id,
            "login": user.login,
            "full_name": user.full_name,
            "role": role,
            "roles": sorted(roles),
            "company_ids": company_ids,
            "branch_ids": branch_ids,
            "permissions": sorted(permissions),
        }
