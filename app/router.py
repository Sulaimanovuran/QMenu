"""Сборка API под namespace /api/v1/{auth,crm,public,kds} (контракт раздел 4).

Внутренние urls.py каждого домена уже содержат "/branches/{branch_id}/..." в
своих путях, поэтому большинство CRM/public роутеров подключаются без
дополнительного префикса — префикс добавляет только namespace-обёртка.
"""
from fastapi import APIRouter

from .users.urls import userRouter
from .companies.urls import companyRouter
from .menu.urls import menuRouter, public_menu_router
from .tables.urls import tableRouter
from .staff.urls import staffRouter
from .sessions.urls import sessionRouter
from .orders.urls import crm_order_router, public_order_router, kds_order_router

api_router = APIRouter()

# ── auth: login/me/refresh/logout ────────────────────────────────────────────
api_router.include_router(userRouter, prefix="/auth", tags=["Auth"])

# ── crm: авторизованные эндпоинты персонала/владельца/супер-админа ───────────
crm_router = APIRouter()
crm_router.include_router(companyRouter, prefix="/companies", tags=["CRM: Companies & Branches"])
crm_router.include_router(menuRouter, tags=["CRM: Menu"])
crm_router.include_router(tableRouter, tags=["CRM: Tables & QR"])
crm_router.include_router(staffRouter, tags=["CRM: Staff"])
crm_router.include_router(crm_order_router, tags=["CRM: Orders & Moderation"])
api_router.include_router(crm_router, prefix="/crm")

# ── public: гостевой контур, без CRM Authorization ───────────────────────────
public_router = APIRouter()
public_router.include_router(sessionRouter, prefix="/sessions", tags=["Public: Table Sessions (guest)"])
public_router.include_router(public_menu_router, tags=["Public: Menu preview"])
public_router.include_router(public_order_router, tags=["Public: Guest Orders"])
api_router.include_router(public_router, prefix="/public")

# ── kds: кухня ────────────────────────────────────────────────────────────────
api_router.include_router(kds_order_router, prefix="/kds", tags=["KDS: Kitchen"])
