"""Бизнес-логика меню. Проверяет принадлежность сущностей филиалу."""
from fastapi import HTTPException, status

from app.common.errors import AppError
from app.models import MenuCategory, MenuItem
from app.common.schemas import (
    CategoryIn, CategoryReorder, CategoryUpdate, ItemReorder,
    MenuCopyFrom, MenuItemAvailability, MenuItemIn, MenuItemUpdate,
)
from .repository import MenuRepository


class MenuService:
    def __init__(self, repo: MenuRepository):
        self.repo = repo

    async def list_categories(self, branch_id: int, limit: int, offset: int) -> tuple[list[MenuCategory], int]:
        return await self.repo.list_categories(branch_id, limit, offset)

    async def create_category(self, branch_id: int, data: CategoryIn) -> MenuCategory:
        return await self.repo.create_category(branch_id, data)

    async def delete_category(self, branch_id: int, category_id: int) -> None:
        cat = await self.repo.get_category(category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
        if await self.repo.category_has_items(category_id):
            raise AppError(
                status.HTTP_409_CONFLICT,
                "CATEGORY_HAS_ITEMS",
                "Нельзя удалить категорию, в которой есть блюда",
            )
        await self.repo.delete_category(cat)

    async def update_category(self, branch_id: int, category_id: int, data: CategoryUpdate):
        cat = await self.repo.get_category(category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
        return await self.repo.update_category(cat, data)

    async def list_items(self, branch_id: int, limit: int, offset: int) -> tuple[list[MenuItem], int]:
        return await self.repo.list_items(branch_id, limit, offset)

    async def create_item(self, branch_id: int, data: MenuItemIn) -> MenuItem:
        cat = await self.repo.get_category(data.category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Категория не принадлежит филиалу"
            )
        return await self.repo.create_item(data)

    async def update_item(
        self, branch_id: int, item_id: int, data: MenuItemUpdate
    ) -> MenuItem:
        item = await self._item_in_branch(branch_id, item_id)
        return await self.repo.update_item(item, data)

    async def delete_item(self, branch_id: int, item_id: int) -> None:
        item = await self._item_in_branch(branch_id, item_id)
        await self.repo.delete_item(item)

    async def set_availability(
        self, branch_id: int, item_id: int, data: MenuItemAvailability
    ) -> MenuItem:
        """Быстрое включение/выключение блюда или отправка в стоп-лист."""
        item = await self._item_in_branch(branch_id, item_id)
        patch = data.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Укажите is_available и/или status"
            )
        for field, value in patch.items():
            setattr(item, field, value)
        await item.save()
        return item

    # ── Порядок категорий и блюд ─────────────────────────────────────────────
    async def reorder_categories(self, branch_id: int, data: CategoryReorder) -> None:
        branch_ids = await self.repo.branch_category_ids(branch_id)
        if set(data.category_ids) - branch_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Некоторые категории не принадлежат этому филиалу",
            )
        await self.repo.set_category_order(data.category_ids)

    async def reorder_items(self, branch_id: int, data: ItemReorder) -> None:
        cat = await self.repo.get_category(data.category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
        cat_item_ids = await self.repo.category_item_ids(data.category_id)
        if set(data.item_ids) - cat_item_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Некоторые позиции не принадлежат этой категории",
            )
        await self.repo.set_item_order(data.item_ids)

    # ── Копирование меню между филиалами ─────────────────────────────────────
    async def copy_from(self, branch_id: int, data: MenuCopyFrom) -> dict:
        """Копирует категории/блюда source-филиала в текущий.

        Проверка доступа к обоим филиалам — на уровне urls (guard по branch_id
        пути + сервисная проверка source ниже через владение категориями не
        требуется: source проверяет отдельный guard в urls).
        """
        if data.source_branch_id == branch_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Нельзя копировать меню из того же филиала"
            )
        source_cats = await self.repo.categories_with_items(data.source_branch_id)
        if not source_cats:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "В исходном филиале нет меню"
            )
        if data.replace_existing:
            await self.repo.delete_branch_menu(branch_id)

        copied_categories = 0
        copied_items = 0
        for src_cat in source_cats:
            if not data.copy_categories:
                break
            new_cat = await self.repo.copy_category(branch_id, src_cat)
            copied_categories += 1
            if data.copy_items:
                for src_item in src_cat.items:
                    await self.repo.copy_item(new_cat.id, src_item)
                    copied_items += 1
        return {
            "copied_categories": copied_categories,
            "copied_items": copied_items,
            "replaced_existing": data.replace_existing,
        }

    async def public_menu(self, branch_id: int) -> list[MenuCategory]:
        return await self.repo.public_menu(branch_id)

    async def _item_in_branch(self, branch_id: int, item_id: int) -> MenuItem:
        item = await self.repo.get_item(item_id)
        if item:
            await item.fetch_related("category")
        if not item or item.category.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Позиция не найдена")
        return item
