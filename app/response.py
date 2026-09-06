from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: list[str] = []

    @classmethod
    def ok(cls, data: T, message: str = "Request successful") -> "ApiResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, errors: list[str] | None = None) -> "ApiResponse[None]":
        return cls(success=False, message=message, data=None, errors=errors or [])
