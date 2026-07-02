"""Утилиты безопасности: токены устройств и зависимости авторизации персонала."""
import secrets
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models import Employee, User
from app.users.service import get_current_user
from app.models.users import GetUser


def new_token(nbytes: int = 24) -> str:
    """Криптостойкий URL-безопасный токен (для qr_token, device_token)."""
    return secrets.token_urlsafe(nbytes)


async def get_current_employee(
    branch_id: int,
    user: GetUser = Depends(get_current_user),  # type: ignore
) -> Optional[Employee]:
    """Текущий пользователь как активный сотрудник конкретного филиала.

    Используется на эндпоинтах персонала (модерация, KDS, управление).
    branch_id берётся из пути. Супер-админ (User.is_superadmin) проходит без
    записи employee — возвращается None, вызывающий код должен это учитывать.
    """
    if user.is_superadmin:
        return None
    employee = (
        await Employee.filter(user_id=user.id, branch_id=branch_id, is_active=True)
        .prefetch_related("role")
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь активным сотрудником этого филиала",
        )
    return employee


async def require_branch_owner(
    branch_id: int,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    """Пускает владельца компании, которой принадлежит филиал, или супер-админа.

    Используется для bootstrap-операций (назначение первых сотрудников),
    где проверка по таблице employee невозможна — владелец ещё не сотрудник.
    """
    from app.models import Branch

    if user.is_superadmin:
        return user

    branch = await Branch.filter(id=branch_id).prefetch_related("company").first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
    if branch.company.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Доступно только владельцу компании"
        )
    return user


def require_manage(*allowed_codes: str):
    """Пускает супер-админа, владельца компании филиала или сотрудника с ролью.

    Решает проблему bootstrap: владелец управляет меню/столами сразу,
    не будучи записанным в employee, а делегированные сотрудники — по роли.
    """

    async def _checker(
        branch_id: int,
        user: GetUser = Depends(get_current_user),  # type: ignore
    ):
        from app.models import Branch, Employee

        if user.is_superadmin:
            return user

        branch = await Branch.filter(id=branch_id).prefetch_related("company").first()
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        if branch.company.owner_id == user.id:
            return user
        emp = (
            await Employee.filter(user_id=user.id, branch_id=branch_id, is_active=True)
            .prefetch_related("role")
            .first()
        )
        if emp and emp.role.code in allowed_codes:
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")

    return _checker


def require_staff_action(*allowed_codes: str):
    """Как require_manage, но возвращает employee_id (или None для владельца/супер-админа).

    Нужно для операций, фиксирующих исполнителя (moderated_by): официант ->
    его employee.id; владелец/супер-админ без записи employee -> None.
    """

    async def _checker(
        branch_id: int,
        user: GetUser = Depends(get_current_user),  # type: ignore
    ) -> Optional[int]:
        from app.models import Branch, Employee

        if user.is_superadmin:
            return None

        branch = await Branch.filter(id=branch_id).prefetch_related("company").first()
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        emp = (
            await Employee.filter(user_id=user.id, branch_id=branch_id, is_active=True)
            .prefetch_related("role")
            .first()
        )
        if emp and emp.role.code in allowed_codes:
            return emp.id
        if branch.company.owner_id == user.id:
            return emp.id if emp else None
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")

    return _checker


def require_roles(*allowed_codes: str):
    """Фабрика зависимости: пускает только сотрудников с нужной ролью (или супер-админа).

    Пример: Depends(require_roles("owner", "branch_admin"))
    """

    async def _checker(
        branch_id: int,
        user: GetUser = Depends(get_current_user),  # type: ignore
        employee: Optional[Employee] = Depends(get_current_employee),
    ) -> Optional[Employee]:
        if user.is_superadmin:
            return employee
        if not employee or employee.role.code not in allowed_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {', '.join(allowed_codes)}",
            )
        return employee

    return _checker


# ── Необязательная авторизация (для эндпоинтов, доступных и гостю, и персоналу) ─
_optional_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def optional_current_user(token: Optional[str] = Depends(_optional_oauth2)):
    """Возвращает пользователя, если есть валидный JWT, иначе None (без ошибки)."""
    if not token:
        return None
    try:
        import jwt
        from config.settings import SECRET_KEY
        from app.models import User

        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = await User.filter(id=payload.get("id")).first()
        return user
    except Exception:
        return None
