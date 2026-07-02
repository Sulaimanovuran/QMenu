"""Единый конверт ответов по контракту: {success,message,data} и {data,pagination}."""
import math
from typing import Any


def ok(data: Any = None, message: str = "OK") -> dict:
    return {"success": True, "message": message, "data": data}


def paginated(items: list, total: int, limit: int, page: int) -> dict:
    last_page = max(1, math.ceil(total / limit)) if limit else 1
    return {
        "data": items,
        "pagination": {
            "current_page": page,
            "last_page": last_page,
            "per_page": limit,
            "total": total,
        },
    }
