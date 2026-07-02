"""Сборка API под namespace /api/v1/{auth,crm,public,kds} (контракт раздел 4).

Внутренние urls.py каждого домена уже содержат "/branches/{branch_id}/..." в
своих путях, поэтому большинство CRM/public роутеров подключаются без
дополнительного префикса — префикс добавляет только namespace-обёртка.

Порядок подключения внутри /crm важен: staffRouter (в т.ч. /users/search)
должен идти раньше crmUsersRouter (/users/{user_id}), иначе "search" попадёт
в {user_id} и вернёт 422.
"""
from fastapi import APIRouter

from .users.urls import userRouter, crmUsersRouter
from .companies.urls import companyRouter, branchOpsRouter
from .menu.urls import menuRouter, public_menu_router
from .tables.urls import tableRouter
from .staff.urls import staffRouter
from .sessions.urls import sessionRouter, crm_session_router
from .orders.urls import crm_order_router, public_order_router, kds_order_router
from .public.urls import publicCatalogRouter
from app.common.uploads import uploadRouter

api_router = APIRouter()

# ── auth: login/me/refresh/logout ────────────────────────────────────────────
api_router.include_router(userRouter, prefix="/auth", tags=["Auth"])

# ── crm: авторизованные эндпоинты персонала/владельца/супер-админа ───────────
crm_router = APIRouter()
crm_router.include_router(companyRouter, prefix="/companies", tags=["CRM: Companies & Branches"])
crm_router.include_router(branchOpsRouter, tags=["CRM: Branch Settings"])
crm_router.include_router(menuRouter, tags=["CRM: Menu"])
crm_router.include_router(tableRouter, tags=["CRM: Tables & QR"])
crm_router.include_router(staffRouter, tags=["CRM: Staff"])
crm_router.include_router(crmUsersRouter, tags=["CRM: Users"])
crm_router.include_router(crm_session_router, tags=["CRM: Sessions"])
crm_router.include_router(crm_order_router, tags=["CRM: Orders & Moderation"])
crm_router.include_router(uploadRouter, tags=["CRM: Uploads"])
api_router.include_router(crm_router, prefix="/crm")

# ── public: гостевой контур, без CRM Authorization ───────────────────────────
public_router = APIRouter()
public_router.include_router(publicCatalogRouter, tags=["Public: Catalog"])
public_router.include_router(sessionRouter, prefix="/sessions", tags=["Public: Table Sessions (guest)"])
public_router.include_router(public_menu_router, tags=["Public: Menu preview"])
public_router.include_router(public_order_router, tags=["Public: Guest Orders"])
api_router.include_router(public_router, prefix="/public")

# ── kds: кухня ────────────────────────────────────────────────────────────────
api_router.include_router(kds_order_router, prefix="/kds", tags=["KDS: Kitchen"])
