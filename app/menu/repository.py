"""Доступ к данным: категории и позиции меню филиала."""
from typing import Optional

from app.models import MenuCategory, MenuItem
from app.common.schemas import CategoryIn, MenuItemIn, MenuItemUpdate


class MenuRepository:
    # ── Категории ────────────────────────────────────────────────────────────
    async def list_categories(self, branch_id: int, limit: int, offset: int) -> tuple[list[MenuCategory], int]:
        qs = MenuCategory.filter(branch_id=branch_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def create_category(self, branch_id: int, data: CategoryIn) -> MenuCategory:
        return await MenuCategory.create(
            branch_id=branch_id, title=data.title, sort_order=data.sort_order
        )

    async def get_category(self, category_id: int) -> Optional[MenuCategory]:
        return await MenuCategory.filter(id=category_id).first()

    async def delete_category(self, category: MenuCategory) -> None:
        await category.delete()

    # ── Позиции ──────────────────────────────────────────────────────────────
    async def list_items(self, branch_id: int, limit: int, offset: int) -> tuple[list[MenuItem], int]:
        qs = MenuItem.filter(category__branch_id=branch_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def get_item(self, item_id: int) -> Optional[MenuItem]:
        return await MenuItem.filter(id=item_id).first()

    async def create_item(self, data: MenuItemIn) -> MenuItem:
        return await MenuItem.create(
            category_id=data.category_id,
            title=data.title,
            description=data.description,
            price_minor=data.price_minor,
            photo_url=data.photo_url,
            sort_order=data.sort_order,
        )

    async def update_item(self, item: MenuItem, data: MenuItemUpdate) -> MenuItem:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await item.save()
        return item

    async def delete_item(self, item: MenuItem) -> None:
        await item.delete()

    async def public_menu(self, branch_id: int) -> list[MenuCategory]:
        """Меню для гостя: активные категории с позициями (без стоп-листа скрывать
        на фронте; здесь отдаём всё с флагом is_in_stoplist)."""
        return (
            await MenuCategory.filter(branch_id=branch_id, is_active=True)
            .prefetch_related("items")
            .all()
        )

    async def update_category(self, category, data):
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        await category.save()
        return category
