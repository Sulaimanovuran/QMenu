"""Эндпоинты меню. Управление — для персонала (CRM); публичное меню — гостю (public)."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Branch, GetCategory, GetMenuItem
from app.models.users import GetUser
from app.users.service import get_current_user
from app.common.schemas import (
    CategoryIn, CategoryReorder, CategoryUpdate, ItemReorder,
    MenuCopyFrom, MenuItemAvailability, MenuItemIn, MenuItemUpdate,
)
from app.common.security import require_manage
from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from .service import MenuService
from .repository import MenuRepository

menuRouter = APIRouter()
public_menu_router = APIRouter()
service = MenuService(MenuRepository())

# роль, которой можно редактировать меню (владелец/супер-админ — отдельная ветка в require_manage)
MANAGE = require_manage("branch_admin")


# ── Публичное меню (гость, без авторизации) ──────────────────────────────────
@public_menu_router.get("/branches/{branch_id}/public-menu")
async def public_menu(branch_id: int):
    cats = await service.public_menu(branch_id)
    return ok([
        {
            "id": c.id,
            "title": c.title,
            "sort_order": c.sort_order,
            "items": [
                {
                    "id": i.id,
                    "title": i.title,
                    "description": i.description,
                    "price_minor": i.price_minor,
                    "photo_url": i.photo_url,
                    "is_in_stoplist": i.is_in_stoplist,
                }
                for i in sorted(c.items, key=lambda x: (x.sort_order, x.id))
            ],
        }
        for c in cats
    ])


# ── Категории (персонал) ─────────────────────────────────────────────────────
@menuRouter.get("/branches/{branch_id}/categories")
async def list_categories(branch_id: int, page: PageParams = Depends(), _=Depends(MANAGE)):
    items, total = await service.list_categories(branch_id, page.limit, page.offset)
    data = [await GetCategory.from_tortoise_orm(c) for c in items]
    return paginated(data, total, page.limit, page.page)


@menuRouter.post("/branches/{branch_id}/categories", status_code=201)
async def create_category(branch_id: int, data: CategoryIn, _=Depends(MANAGE)):
    cat = await service.create_category(branch_id, data)
    return ok(await GetCategory.from_tortoise_orm(cat), "Категория создана")


@menuRouter.patch("/branches/{branch_id}/categories/{category_id}")
async def update_category(
    branch_id: int, category_id: int, data: CategoryUpdate, _=Depends(MANAGE)
):
    cat = await service.update_category(branch_id, category_id, data)
    return ok(await GetCategory.from_tortoise_orm(cat))


@menuRouter.delete("/branches/{branch_id}/categories/{category_id}", status_code=204)
async def delete_category(branch_id: int, category_id: int, _=Depends(MANAGE)):
    await service.delete_category(branch_id, category_id)


# ── Позиции (персонал) ───────────────────────────────────────────────────────
@menuRouter.get("/branches/{branch_id}/items")
async def list_items(branch_id: int, page: PageParams = Depends(), _=Depends(MANAGE)):
    items, total = await service.list_items(branch_id, page.limit, page.offset)
    data = [await GetMenuItem.from_tortoise_orm(i) for i in items]
    return paginated(data, total, page.limit, page.page)


@menuRouter.post("/branches/{branch_id}/items", status_code=201)
async def create_item(branch_id: int, data: MenuItemIn, _=Depends(MANAGE)):
    item = await service.create_item(branch_id, data)
    return ok(await GetMenuItem.from_tortoise_orm(item), "Позиция создана")


@menuRouter.patch("/branches/{branch_id}/items/{item_id}")
async def update_item(
    branch_id: int, item_id: int, data: MenuItemUpdate, _=Depends(MANAGE)
):
    item = await service.update_item(branch_id, item_id, data)
    return ok(await GetMenuItem.from_tortoise_orm(item))


@menuRouter.delete("/branches/{branch_id}/items/{item_id}", status_code=204)
async def delete_item(branch_id: int, item_id: int, _=Depends(MANAGE)):
    await service.delete_item(branch_id, item_id)


@menuRouter.post("/branches/{branch_id}/items/{item_id}/availability")
async def set_item_availability(
    branch_id: int, item_id: int, data: MenuItemAvailability, _=Depends(MANAGE)
):
    """Быстро включить/выключить блюдо или отправить в стоп-лист."""
    item = await service.set_availability(branch_id, item_id, data)
    return ok(await GetMenuItem.from_tortoise_orm(item), "Доступность обновлена")


# ── Порядок категорий и блюд ─────────────────────────────────────────────────
@menuRouter.post("/branches/{branch_id}/categories/reorder")
async def reorder_categories(branch_id: int, data: CategoryReorder, _=Depends(MANAGE)):
    await service.reorder_categories(branch_id, data)
    return ok(None, "Порядок категорий обновлён")


@menuRouter.post("/branches/{branch_id}/items/reorder")
async def reorder_items(branch_id: int, data: ItemReorder, _=Depends(MANAGE)):
    await service.reorder_items(branch_id, data)
    return ok(None, "Порядок блюд обновлён")


# ── Копирование меню между филиалами (owner/super_admin) ─────────────────────
@menuRouter.post("/branches/{branch_id}/menu/copy-from")
async def copy_menu_from(
    branch_id: int,
    data: MenuCopyFrom,
    user: GetUser = Depends(get_current_user),  # type: ignore
):
    """Скопировать категории/блюда из другого филиала в текущий."""
    # доступ к обоим филиалам: супер-админ или владелец компаний обоих филиалов
    if not user.is_superadmin:
        for bid in (branch_id, data.source_branch_id):
            branch = await Branch.filter(id=bid).prefetch_related("company").first()
            if not branch:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
            if branch.company.owner_id != user.id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Копировать меню может только владелец обоих филиалов",
                )
    result = await service.copy_from(branch_id, data)
    return ok(result, "Меню скопировано")
