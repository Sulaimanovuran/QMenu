"""Публичный Guest-каталог: сериализация без приватных полей + is_open/type_title."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status

from app.models import Company, RestaurantType
from .repository import PublicRepository


class PublicService:
    def __init__(self, repo: PublicRepository):
        self.repo = repo

    # ── Типы заведений ─────────────────────────────────────────────────────────
    async def _type_title_map(self) -> dict[str, str]:
        types = await RestaurantType.all()
        return {t.code: t.title for t in types}

    async def restaurant_types(self) -> list[dict]:
        types = await self.repo.restaurant_types()
        return [
            {
                "id": t.id,
                "code": t.code,
                "title": t.title,
                "image_url": t.image_url,
                "sort_order": t.sort_order,
                "is_active": t.is_active,
            }
            for t in types
        ]

    # ── Заведения ──────────────────────────────────────────────────────────────
    async def list_places(
        self, limit, offset, search=None, type_codes=None, city=None
    ) -> tuple[list[dict], int]:
        items, total = await self.repo.list_places(limit, offset, search, type_codes, city)
        tmap = await self._type_title_map()
        result = []
        for c in items:
            count = await self.repo.branches_count(c.id)
            result.append(self._place_list_item(c, tmap, count))
        return result, total

    async def place_details(self, slug: str) -> dict:
        company = await self.repo.get_place(slug)
        if not company:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заведение не найдено")
        tmap = await self._type_title_map()
        branches, _ = await self.repo.place_branches(company.id, limit=100, offset=0)
        return {
            "id": company.id,
            "slug": company.slug,
            "title": company.title,
            "description": company.description,
            "type_ids": company.type_codes or [],
            "type_title": self._type_title(company, tmap),
            "logo_url": company.logo_url,
            "cover_url": company.cover_url,
            "branches": [self._branch_list_item(b) for b in branches],
        }

    async def place_branches(self, slug: str, limit, offset, city=None) -> tuple[list[dict], int]:
        company = await self.repo.get_place(slug)
        if not company:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Заведение не найдено")
        branches, total = await self.repo.place_branches(company.id, limit, offset, city)
        return [self._branch_list_item(b) for b in branches], total

    async def branch_details(self, slug: str) -> dict:
        branch = await self.repo.get_branch(slug)
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        tmap = await self._type_title_map()
        return self._branch_details(branch, tmap)

    # ── Меню ───────────────────────────────────────────────────────────────────
    async def branch_menu(self, slug: str) -> dict:
        branch = await self.repo.get_branch(slug)
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        tmap = await self._type_title_map()
        cats = await self.repo.branch_menu(branch.id)
        return {
            "place": self._place_summary(branch.company, tmap),
            "branch": self._branch_details(branch, tmap),
            "categories": [self._menu_category(cat) for cat in cats],
        }

    async def menu_via_place(self, place_slug: str, branch_slug: str) -> dict:
        menu = await self.branch_menu(branch_slug)
        if menu["place"]["slug"] != place_slug:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден в этом заведении")
        return menu

    async def item_details(self, branch_slug: str, item_id: int) -> dict:
        branch = await self.repo.get_branch(branch_slug)
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        item = await self.repo.get_item(branch.id, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Блюдо не найдено")
        data = self._menu_item(item)
        data["category"] = {"id": item.category.id, "title": item.category.title}
        return data

    async def search_items(
        self, branch_slug: str, limit, offset, search=None, category_id=None, is_available=None
    ) -> tuple[list[dict], int]:
        branch = await self.repo.get_branch(branch_slug)
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Филиал не найден")
        items, total = await self.repo.search_items(
            branch.id, limit, offset, search, category_id, is_available
        )
        return [self._menu_item(i) for i in items], total

    # ── Стол по QR ─────────────────────────────────────────────────────────────
    async def table_preview(self, qr_token: str) -> dict:
        table = await self.repo.get_table_by_qr(qr_token)
        if not table:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Стол не найден")
        tmap = await self._type_title_map()
        branch = table.branch
        return {
            "qr_token": table.qr_token,
            "table_title": table.title or table.number,
            "table_zone": table.zone,
            "branch": self._branch_details(branch, tmap),
            "place": self._place_summary(branch.company, tmap),
        }

    # ── helpers ────────────────────────────────────────────────────────────────
    def _type_title(self, company: Company, tmap: dict[str, str]) -> str:
        return ", ".join(tmap.get(code, code) for code in (company.type_codes or []))

    def _place_list_item(self, c: Company, tmap: dict, branches_count: int) -> dict:
        return {
            "id": c.id,
            "slug": c.slug,
            "title": c.title,
            "short_description": c.short_description,
            "type_ids": c.type_codes or [],
            "type_title": self._type_title(c, tmap),
            "logo_url": c.logo_url,
            "cover_url": c.cover_url,
            "branches_count": branches_count,
        }

    def _place_summary(self, c: Company, tmap: dict) -> dict:
        return {
            "id": c.id,
            "slug": c.slug,
            "title": c.title,
            "type_title": self._type_title(c, tmap),
            "logo_url": c.logo_url,
            "cover_url": c.cover_url,
        }

    def _branch_list_item(self, b) -> dict:
        return {
            "id": b.id,
            "slug": b.slug,
            "title": b.title,
            "address": b.address,
            "city": b.city,
            "cover_url": b.cover_url,
            "working_hours": b.working_hours,
            "is_open": self._is_open(b),
        }

    def _branch_details(self, b, tmap: dict) -> dict:
        data = self._branch_list_item(b)
        data["place"] = self._place_summary(b.company, tmap) if b.company else None
        return data

    def _menu_category(self, cat) -> dict:
        items = sorted(cat.items, key=lambda x: (x.sort_order, x.id))
        return {
            "id": cat.id,
            "slug": cat.slug,
            "title": cat.title,
            "sort_order": cat.sort_order,
            "items": [self._menu_item(i) for i in items if i.is_published],
        }

    def _menu_item(self, i) -> dict:
        return {
            "id": i.id,
            "title": i.title,
            "description": i.description,
            "image_url": i.image_url,
            "price_minor": i.price_minor,
            "weight": i.weight,
            "weight_unit": i.weight_unit,
            "is_available": i.is_available and i.status != i.STOP_LIST,
        }

    def _is_open(self, branch) -> bool:
        """Открыт ли филиал сейчас по schedule. Пустой график -> считаем открытым."""
        schedule = branch.schedule or []
        if not schedule:
            return branch.is_active
        now = datetime.now()
        today = now.weekday() + 1  # 1=Пн .. 7=Вс
        day = next((d for d in schedule if d.get("day_of_week") == today), None)
        if not day or day.get("is_closed"):
            return False
        try:
            opens = day.get("opens_at", "00:00")
            closes = day.get("closes_at", "23:59")
            cur = now.strftime("%H:%M")
            if closes <= opens:  # через полночь
                return cur >= opens or cur <= closes
            return opens <= cur <= closes
        except Exception:
            return True
