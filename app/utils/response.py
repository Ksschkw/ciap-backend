from __future__ import annotations

from typing import Any


def build_response(
    *,
    success: bool,
    message: str,
    data: Any = None,
    meta: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    if error is not None:
        payload["error"] = error
    return payload


def success_response(message: str, data: Any = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_response(success=True, message=message, data=data, meta=meta)


def error_response(message: str, code: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code}
    if details is not None:
        error["details"] = details
    return build_response(success=False, message=message, error=error)
