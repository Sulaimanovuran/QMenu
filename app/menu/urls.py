"""Эндпоинты меню. Управление — для персонала; публичное меню — открыто гостю."""
from fastapi import APIRouter, Depends

from app.models import GetCategory, GetMenuItem
from app.common.schemas import CategoryIn, MenuItemIn, MenuItemUpdate
from app.common.security import require_manage
from .service import MenuService
from .repository import MenuRepository

menuRouter = APIRouter()
service = MenuService(MenuRepository())

# роли, которым можно редактировать меню
MANAGE = require_manage("admin", "manager")


# ── Публичное меню (гость, без авторизации) ──────────────────────────────────
@menuRouter.get("/branches/{branch_id}/public-menu")
async def public_menu(branch_id: int):
    cats = await service.public_menu(branch_id)
    return [
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
    ]


# ── Категории (персонал) ─────────────────────────────────────────────────────
@menuRouter.get("/branches/{branch_id}/categories", response_model=list[GetCategory])
async def list_categories(branch_id: int):
    return await service.list_categories(branch_id)


@menuRouter.post(
    "/branches/{branch_id}/categories", response_model=GetCategory, status_code=201
)
async def create_category(
    branch_id: int, data: CategoryIn, _=Depends(MANAGE)
):
    cat = await service.create_category(branch_id, data)
    return await GetCategory.from_tortoise_orm(cat)


@menuRouter.delete(
    "/branches/{branch_id}/categories/{category_id}", status_code=204
)
async def delete_category(branch_id: int, category_id: int, _=Depends(MANAGE)):
    await service.delete_category(branch_id, category_id)


# ── Позиции (персонал) ───────────────────────────────────────────────────────
@menuRouter.get("/branches/{branch_id}/items", response_model=list[GetMenuItem])
async def list_items(branch_id: int):
    return await service.list_items(branch_id)


@menuRouter.post(
    "/branches/{branch_id}/items", response_model=GetMenuItem, status_code=201
)
async def create_item(branch_id: int, data: MenuItemIn, _=Depends(MANAGE)):
    item = await service.create_item(branch_id, data)
    return await GetMenuItem.from_tortoise_orm(item)


@menuRouter.patch(
    "/branches/{branch_id}/items/{item_id}", response_model=GetMenuItem
)
async def update_item(
    branch_id: int, item_id: int, data: MenuItemUpdate, _=Depends(MANAGE)
):
    item = await service.update_item(branch_id, item_id, data)
    return await GetMenuItem.from_tortoise_orm(item)


@menuRouter.delete("/branches/{branch_id}/items/{item_id}", status_code=204)
async def delete_item(branch_id: int, item_id: int, _=Depends(MANAGE)):
    await service.delete_item(branch_id, item_id)
