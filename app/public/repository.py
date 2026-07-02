"""Доступ к данным для публичного Guest-каталога.

Отдаёт только опубликованные и активные сущности (is_active & is_published),
без CRM/приватных полей.
"""
from typing import Optional

from tortoise.expressions import Q

from app.models import Branch, Company, MenuCategory, MenuItem, RestaurantType, Table


class PublicRepository:
    # ── Типы заведений ─────────────────────────────────────────────────────────
    async def restaurant_types(self) -> list[RestaurantType]:
        return await RestaurantType.filter(is_active=True).all()

    # ── Заведения (компании) ───────────────────────────────────────────────────
    async def list_places(
        self,
        limit: int,
        offset: int,
        search: Optional[str] = None,
        type_codes: Optional[list[str]] = None,
        city: Optional[str] = None,
    ) -> tuple[list[Company], int]:
        qs = Company.filter(is_active=True, is_published=True)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(short_description__icontains=search)
            )
        # фильтр по городу — по наличию опубликованного филиала в этом городе
        if city:
            qs = qs.filter(branches__city__iexact=city, branches__is_published=True).distinct()
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()

        if type_codes:
            # type_codes хранятся в JSON-списке; фильтруем в Python (без изменения выборки total —
            # для MVP приемлемо, т.к. каталог небольшой)
            wanted = set(type_codes)
            items = [c for c in items if wanted & set(c.type_codes or [])]
        return items, total

    async def get_place(self, slug: str) -> Optional[Company]:
        return await Company.filter(slug=slug, is_active=True, is_published=True).first()

    async def place_branches(
        self,
        company_id: int,
        limit: int,
        offset: int,
        city: Optional[str] = None,
    ) -> tuple[list[Branch], int]:
        qs = Branch.filter(company_id=company_id, is_active=True, is_published=True)
        if city:
            qs = qs.filter(city__iexact=city)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def branches_count(self, company_id: int) -> int:
        return await Branch.filter(
            company_id=company_id, is_active=True, is_published=True
        ).count()

    # ── Филиалы ────────────────────────────────────────────────────────────────
    async def get_branch(self, slug: str) -> Optional[Branch]:
        return (
            await Branch.filter(slug=slug, is_active=True, is_published=True)
            .prefetch_related("company")
            .first()
        )

    # ── Меню ───────────────────────────────────────────────────────────────────
    async def branch_menu(self, branch_id: int) -> list[MenuCategory]:
        return (
            await MenuCategory.filter(
                branch_id=branch_id, is_active=True, is_published=True
            )
            .prefetch_related("items")
            .all()
        )

    async def get_item(self, branch_id: int, item_id: int) -> Optional[MenuItem]:
        return (
            await MenuItem.filter(
                id=item_id, category__branch_id=branch_id, is_published=True
            )
            .prefetch_related("category")
            .first()
        )

    async def search_items(
        self,
        branch_id: int,
        limit: int,
        offset: int,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
    ) -> tuple[list[MenuItem], int]:
        qs = MenuItem.filter(category__branch_id=branch_id, is_published=True)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        if is_available is not None:
            qs = qs.filter(is_available=is_available)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    # ── Столы ──────────────────────────────────────────────────────────────────
    async def get_table_by_qr(self, qr_token: str) -> Optional[Table]:
        return (
            await Table.filter(qr_token=qr_token, is_active=True)
            .prefetch_related("branch__company")
            .first()
        )
