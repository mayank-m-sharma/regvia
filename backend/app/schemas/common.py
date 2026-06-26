from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    message: str
    code: str


class ApiResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: T | None
    error: ApiError | None = None
