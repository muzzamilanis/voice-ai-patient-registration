"""Consistent JSON envelope helpers required by the assessment."""

from typing import Any

from fastapi.responses import JSONResponse


def success(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": data, "error": None})


def failure(message: str, status_code: int = 400, details: Any = None) -> JSONResponse:
    error: dict[str, Any] = {"message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"data": None, "error": error})
