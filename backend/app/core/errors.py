"""
Единый формат ошибок API.

Любая ошибка бизнес-логики возвращается так:
    {"code": "MACHINE_CODE", "message": "Человеческое сообщение", "detail": "то же сообщение"}
Для 422 дополнительно: "fields": {"имя_поля": "что не так"}.
Фронтенд показывает `detail` пользователю, а по `code` может принимать решения
(например, при GRADE_COOLDOWN показать таймер).
"""
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: str | list
    fields: dict[str, str] | None = None


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, detail: str, code: str | None = None, extra: dict | None = None,
                 headers: dict | None = None):
        self.detail = detail
        self.headers = headers
        if code:
            self.code = code
        self.extra = extra or {}


class BadRequest(AppError):
    status_code, code = 400, "BAD_REQUEST"


class Unauthorized(AppError):
    status_code, code = 401, "UNAUTHORIZED"


class Forbidden(AppError):
    status_code, code = 403, "FORBIDDEN"


class NotFound(AppError):
    status_code, code = 404, "NOT_FOUND"


class Conflict(AppError):
    status_code, code = 409, "CONFLICT"


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"code": exc.code, "message": exc.detail, "detail": exc.detail, **exc.extra})


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """
    422: неверные поля. Помимо стандартного списка FastAPI (`detail`) отдаём `fields`:
    {"salary_to": "Зарплата «до» не может быть меньше зарплаты «от»"} — фронт подсвечивает поле формы.
    """
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x not in ("body", "query", "path")]
        name = loc[0] if loc else "_"
        msg = str(err.get("msg", "")).removeprefix("Value error, ")
        fields.setdefault(name, msg)
    return JSONResponse(status_code=422, content={
        "code": "VALIDATION_ERROR", "message": "Проверьте правильность заполнения полей",
        "fields": fields, "detail": jsonable_encoder(exc.errors())})


# Готовые описания ошибок для Swagger (подставляются в responses=... у роутов)
def errors(*codes: int) -> dict:
    names = {400: "Некорректный запрос", 401: "Нет или неверный токен", 403: "Недостаточно прав",
             404: "Не найдено", 409: "Конфликт с текущим состоянием", 429: "Слишком много запросов"}
    return {c: {"model": ErrorResponse, "description": names.get(c, "Ошибка")} for c in codes}
