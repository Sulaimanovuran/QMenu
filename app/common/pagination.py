"""Общая зависимость пагинации: limit/offset/page, как описано в контракте."""
from fastapi import Query


class PageParams:
    def __init__(
        self,
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
        page: int | None = Query(None, ge=1),
    ):
        self.limit = limit
        self.page = page if page is not None else (offset // limit) + 1
        self.offset = (self.page - 1) * limit if page is not None else offset
