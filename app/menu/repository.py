"""Доступ к данным: категории и позиции меню филиала."""
from typing import Optional

from app.models import MenuCategory, MenuItem
from app.common.schemas import CategoryIn, MenuItemIn, MenuItemUpdate
from app.common.slug import unique_slug


class MenuRepository:
    # ── Категории ────────────────────────────────────────────────────────────
    async def list_categories(self, branch_id: int, limit: int, offset: int) -> tuple[list[MenuCategory], int]:
        qs = MenuCategory.filter(branch_id=branch_id)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit).all()
        return items, total

    async def create_category(self, branch_id: int, data: CategoryIn) -> MenuCategory:
        slug = await unique_slug(MenuCategory, data.title)
        return await MenuCategory.create(
            branch_id=branch_id,
            slug=slug,
            title=data.title,
            description=data.description,
            image_url=data.image_url,
            sort_order=data.sort_order,
            is_active=data.is_active,
            is_published=data.is_published,
        )

    async def get_category(self, category_id: int) -> Optional[MenuCategory]:
        return await MenuCategory.filter(id=category_id).first()

    async def delete_category(self, category: MenuCategory) -> None:
        await category.delete()

    async def category_has_items(self, category_id: int) -> bool:
        return await MenuItem.filter(category_id=category_id).exists()

    async def branch_category_ids(self, branch_id: int) -> set[int]:
        rows = await MenuCategory.filter(branch_id=branch_id).values_list("id", flat=True)
        return set(rows)

    async def category_item_ids(self, category_id: int) -> set[int]:
        rows = await MenuItem.filter(category_id=category_id).values_list("id", flat=True)
        return set(rows)

    async def set_category_order(self, ordered_ids: list[int]) -> None:
        for pos, cat_id in enumerate(ordered_ids):
            await MenuCategory.filter(id=cat_id).update(sort_order=pos)

    async def set_item_order(self, ordered_ids: list[int]) -> None:
        for pos, item_id in enumerate(ordered_ids):
            await MenuItem.filter(id=item_id).update(sort_order=pos)

    async def categories_with_items(self, branch_id: int) -> list[MenuCategory]:
        return (
            await MenuCategory.filter(branch_id=branch_id)
            .prefetch_related("items")
            .all()
        )

    async def delete_branch_menu(self, branch_id: int) -> None:
        """Полная очистка меню филиала (items уходят каскадом за категориями)."""
        await MenuCategory.filter(branch_id=branch_id).delete()

    async def copy_category(self, dst_branch_id: int, src: MenuCategory) -> MenuCategory:
        slug = await unique_slug(MenuCategory, src.title)
        return await MenuCategory.create(
            branch_id=dst_branch_id,
            slug=slug,
            title=src.title,
            description=src.description,
            image_url=src.image_url,
            sort_order=src.sort_order,
            is_active=src.is_active,
            is_published=src.is_published,
        )

    async def copy_item(self, dst_category_id: int, src: MenuItem) -> MenuItem:
        return await MenuItem.create(
            category_id=dst_category_id,
            title=src.title,
            description=src.description,
            price_minor=src.price_minor,
            image_url=src.image_url,          # картинки переиспользуются по URL
            weight=src.weight,
            weight_unit=src.weight_unit,
            sort_order=src.sort_order,
            status=src.status,
            is_available=src.is_available,
            is_published=src.is_published,
            cooking_zone=src.cooking_zone,
        )

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
            image_url=data.image_url,
            weight=data.weight,
            weight_unit=data.weight_unit,
            sort_order=data.sort_order,
            status=data.status,
            is_available=data.is_available,
            is_published=data.is_published,
            cooking_zone=data.cooking_zone,
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
