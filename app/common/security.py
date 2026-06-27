"""Утилиты безопасности: токены устройств и зависимости авторизации персонала."""
import secrets
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status

from app.models import Employee, User
from app.users.service import get_current_user
from app.models.users import GetUser


def new_token(nbytes: int = 24) -> str:
    """Криптостойкий URL-безопасный токен (для qr_token, device_token)."""
    return secrets.token_urlsafe(nbytes)


async def get_current_employee(
    branch_id: int,
    user: GetUser = Depends(get_current_user),  # type: ignore
) -> Employee:
    """Текущий пользователь как активный сотрудник конкретного филиала.

    Используется на эндпоинтах персонала (модерация, KDS, управление).
    branch_id берётся из пути.
    """
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
    """Пускает владельца компании, которой принадлежит филиал.

    Используется для bootstrap-операций (назначение первых сотрудников),
    где проверка по таблице employee невозможна — владелец ещё не сотрудник.
    """
    from app.models import Branch

    branch = await Branch.filter(id=branch_id).prefetch_related("company").first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
    if branch.company.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Доступно только владельцу компании"
        )
    return user


def require_manage(*allowed_codes: str):
    """Пускает либо владельца компании филиала, либо сотрудника с нужной ролью.

    Решает проблему bootstrap: владелец управляет меню/столами сразу,
    не будучи записанным в employee, а делегированные сотрудники — по роли.
    """

    async def _checker(
        branch_id: int,
        user: GetUser = Depends(get_current_user),  # type: ignore
    ):
        from app.models import Branch, Employee

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
    """Как require_manage, но возвращает employee_id (или None для владельца).

    Нужно для операций, фиксирующих исполнителя (moderated_by): официант ->
    его employee.id; владелец без записи employee -> None.
    """

    async def _checker(
        branch_id: int,
        user: GetUser = Depends(get_current_user),  # type: ignore
    ) -> Optional[int]:
        from app.models import Branch, Employee

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
    """Фабрика зависимости: пускает только сотрудников с нужной ролью.

    Пример: Depends(require_roles("owner", "admin", "manager"))
    """

    async def _checker(employee: Employee = Depends(get_current_employee)) -> Employee:
        if employee.role.code not in allowed_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {', '.join(allowed_codes)}",
            )
        return employee

    return _checker
