"""Бизнес-логика меню. Проверяет принадлежность сущностей филиалу."""
from fastapi import HTTPException, status

from app.models import MenuCategory, MenuItem
from app.common.schemas import CategoryIn, CategoryUpdate, MenuItemIn, MenuItemUpdate
from .repository import MenuRepository


class MenuService:
    def __init__(self, repo: MenuRepository):
        self.repo = repo

    async def list_categories(self, branch_id: int) -> list[MenuCategory]:
        return await self.repo.list_categories(branch_id)

    async def create_category(self, branch_id: int, data: CategoryIn) -> MenuCategory:
        return await self.repo.create_category(branch_id, data)

    async def delete_category(self, branch_id: int, category_id: int) -> None:
        cat = await self.repo.get_category(category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
        await self.repo.delete_category(cat)

    async def update_category(self, branch_id: int, category_id: int, data: CategoryUpdate):
        cat = await self.repo.get_category(category_id)
        if not cat or cat.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
        return await self.repo.update_category(cat, data)

    async def list_items(self, branch_id: int) -> list[MenuItem]:
        return await self.repo.list_items(branch_id)

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

    async def public_menu(self, branch_id: int) -> list[MenuCategory]:
        return await self.repo.public_menu(branch_id)

    async def _item_in_branch(self, branch_id: int, item_id: int) -> MenuItem:
        item = await self.repo.get_item(item_id)
        if item:
            await item.fetch_related("category")
        if not item or item.category.branch_id != branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Позиция не найдена")
        return item
