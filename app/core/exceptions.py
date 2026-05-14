from __future__ import annotations

from fastapi import HTTPException, status


class CIAPException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(CIAPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(CIAPException):
    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ConflictError(CIAPException):
    def __init__(self, detail: str = "Conflict") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class ForbiddenError(CIAPException):
    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)
