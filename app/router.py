from fastapi import APIRouter

from .users.urls import userRouter
from .companies.urls import companyRouter
from .menu.urls import menuRouter
from .tables.urls import tableRouter
from .staff.urls import staffRouter
from .sessions.urls import sessionRouter
from .orders.urls import orderRouter

api_router = APIRouter()

api_router.include_router(userRouter, prefix="/user", tags=["Users"])
api_router.include_router(companyRouter, prefix="/companies", tags=["Companies & Branches"])
api_router.include_router(menuRouter, prefix="/menu", tags=["Menu"])
api_router.include_router(tableRouter, prefix="/tables", tags=["Tables & QR"])
api_router.include_router(staffRouter, prefix="/staff", tags=["Staff"])
api_router.include_router(sessionRouter, prefix="/sessions", tags=["Table Sessions (guest)"])
api_router.include_router(orderRouter, prefix="/orders", tags=["Orders & Moderation"])
