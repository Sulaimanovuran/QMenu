from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from config import settings
from app.router import api_router
from app.common.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # сидируем фиксированные роли и стартового админа
    from app.common.roles import seed_roles
    from app.users.service import UserService
    from app.users.repository import UserRepository

    await seed_roles()
    await UserService(UserRepository()).create_admin()
    yield


app = FastAPI(
    title="QMENU API",
    version="0.1.0",
    description="QR-меню: компании, филиалы, меню, столы, сессии (mCafe), модерация заказов.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


register_tortoise(
    app,
    db_url=settings.DB_URL,
    modules={"models": settings.APPS_MODEL},
    generate_schemas=True,
    add_exception_handlers=True,
)
