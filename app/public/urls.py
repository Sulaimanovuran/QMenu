"""Публичный Guest-каталог (без CRM Authorization): заведения, филиалы, меню."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.common.pagination import PageParams
from app.common.responses import ok, paginated
from .service import PublicService
from .repository import PublicRepository

publicCatalogRouter = APIRouter()
service = PublicService(PublicRepository())


def _csv(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


@publicCatalogRouter.get("/restaurant-types")
async def restaurant_types():
    return ok(await service.restaurant_types())


@publicCatalogRouter.get("/places")
async def list_places(
    page: PageParams = Depends(),
    search: Optional[str] = Query(None),
    type_ids: Optional[str] = Query(None, description="csv кодов типов"),
    city: Optional[str] = Query(None),
):
    items, total = await service.list_places(
        page.limit, page.offset, search, _csv(type_ids), city
    )
    return paginated(items, total, page.limit, page.page)


@publicCatalogRouter.get("/places/{place_slug}")
async def place_details(place_slug: str):
    return ok(await service.place_details(place_slug))


@publicCatalogRouter.get("/places/{place_slug}/branches")
async def place_branches(
    place_slug: str, page: PageParams = Depends(), city: Optional[str] = Query(None)
):
    items, total = await service.place_branches(place_slug, page.limit, page.offset, city)
    return paginated(items, total, page.limit, page.page)


@publicCatalogRouter.get("/places/{place_slug}/branches/{branch_slug}/menu")
async def menu_via_place(place_slug: str, branch_slug: str):
    return ok(await service.menu_via_place(place_slug, branch_slug))


@publicCatalogRouter.get("/branches/{branch_slug}")
async def branch_details(branch_slug: str):
    return ok(await service.branch_details(branch_slug))


@publicCatalogRouter.get("/branches/{branch_slug}/menu")
async def branch_menu(branch_slug: str):
    return ok(await service.branch_menu(branch_slug))


@publicCatalogRouter.get("/branches/{branch_slug}/menu/search")
async def menu_search(
    branch_slug: str,
    page: PageParams = Depends(),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
):
    items, total = await service.search_items(
        branch_slug, page.limit, page.offset, search, category_id, is_available
    )
    return paginated(items, total, page.limit, page.page)


@publicCatalogRouter.get("/branches/{branch_slug}/menu/items/{item_id}")
async def item_details(branch_slug: str, item_id: int):
    return ok(await service.item_details(branch_slug, item_id))


@publicCatalogRouter.get("/tables/{qr_token}")
async def table_preview(qr_token: str):
    return ok(await service.table_preview(qr_token))
