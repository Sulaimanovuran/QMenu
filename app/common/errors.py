"""Единый формат ошибок по контракту: {success,message,code,field_errors?}."""
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Ошибка приложения с пользовательским текстом и машинным кодом."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field_errors: dict[str, list[str]] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field_errors = field_errors


# соответствие HTTP-статуса стандартному коду для generic HTTPException,
# которые раньше поднимались как raise HTTPException(status, "текст")
_STATUS_TO_CODE = {
    401: "INVALID_CREDENTIALS",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
}


def _error_body(message: str, code: str, field_errors: dict | None = None) -> dict:
    body = {"success": False, "message": message, "code": code}
    if field_errors:
        body["field_errors"] = field_errors
    return body


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.message, exc.code, exc.field_errors),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = _STATUS_TO_CODE.get(exc.status_code, "ACTION_FAILED")
    message = exc.detail if isinstance(exc.detail, str) else "Не удалось выполнить действие"
    return JSONResponse(status_code=exc.status_code, content=_error_body(message, code))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    field_errors: dict[str, list[str]] = {}
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        field = loc[-1] if loc else "__root__"
        field_errors.setdefault(field, []).append(err["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "Проверьте поля формы", "VALIDATION_ERROR", field_errors
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("Внутренняя ошибка сервера", "INTERNAL_ERROR"),
    )
