"""Эндпоинты меню. Управление — для персонала (CRM); публичное меню — гостю (public)."""
from fastapi import APIRouter, Depends

from app.models import GetCategory, GetMenuItem
from app.common.schemas import CategoryIn, CategoryUpdate, MenuItemIn, MenuItemUpdate
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
