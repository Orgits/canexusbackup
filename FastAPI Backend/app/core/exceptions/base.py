from typing import Any

from fastapi import HTTPException, status


class CAException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str = "ERROR",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.extra = extra or {}


class ValidationException(CAException):
    def __init__(
        self,
        detail: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class NotFoundException(CAException):
    def __init__(
        self,
        detail: str = "Resource not found",
        code: str = "NOT_FOUND",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class ConflictException(CAException):
    def __init__(
        self,
        detail: str = "Resource conflict",
        code: str = "CONFLICT",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class UnauthorizedException(CAException):
    def __init__(
        self,
        detail: str = "Unauthorized",
        code: str = "UNAUTHORIZED",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code=code,
            headers=headers or {"WWW-Authenticate": "Bearer"},
            extra=extra,
        )


class ForbiddenException(CAException):
    def __init__(
        self,
        detail: str = "Forbidden",
        code: str = "FORBIDDEN",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class InternalServerException(CAException):
    def __init__(
        self,
        detail: str = "Internal server error",
        code: str = "INTERNAL_ERROR",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class StorageException(CAException):
    def __init__(
        self,
        detail: str = "Storage operation failed",
        code: str = "STORAGE_ERROR",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )


class MalwareException(CAException):
    def __init__(
        self,
        detail: str = "Malware detected",
        code: str = "MALWARE_DETECTED",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code=code,
            headers=headers,
            extra=extra,
        )