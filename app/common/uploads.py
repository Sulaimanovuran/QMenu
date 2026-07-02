"""Сохранение загруженных изображений в UPLOAD_DIR и выдача URL."""
import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.common.errors import AppError
from app.common.responses import ok
from app.users.service import get_current_user
from config import settings

_ALLOWED = {
    "image/jpeg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def save_image(file: UploadFile) -> str:
    """Валидирует и сохраняет картинку, возвращает публичный URL."""
    ext = _ALLOWED.get((file.content_type or "").lower())
    if not ext:
        raise AppError(
            status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR",
            "Проверьте поля формы",
            {"file": ["Допустимы только изображения JPEG/PNG/WebP/GIF"]},
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise AppError(
            status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR",
            "Проверьте поля формы",
            {"file": [f"Файл слишком большой (максимум {mb} МБ)"]},
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(settings.UPLOAD_DIR, name), "wb") as f:
        f.write(content)

    return f"{settings.MEDIA_BASE_URL}/uploads/{name}"


# ── Роутер загрузки (CRM) ─────────────────────────────────────────────────────
uploadRouter = APIRouter()


@uploadRouter.post("/uploads")
async def upload_image(file: UploadFile = File(...), _user=Depends(get_current_user)):
    """Загрузить картинку (multipart) и получить её URL для *_url полей.

    Frontend: сначала грузит файл сюда, затем шлёт полученный image_url/logo_url/
    cover_url в JSON-теле create/update. Так контракт «файлы через multipart,
    backend возвращает URL» выполняется без перевода всех CRUD на form-data.
    """
    url = await save_image(file)
    return ok({"image_url": url}, "Файл загружен")
