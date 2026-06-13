from typing import Generic, TypeVar, Optional, Any, Union
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class MetaPagination(BaseModel):
    total: int
    page: int
    page_size: int

class MetaErrorDetails(BaseModel):
    code: str
    message: str
    field: Optional[str] = None

class MetaError(BaseModel):
    error: MetaErrorDetails

class ResponseEnvelope(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: Optional[Union[MetaPagination, MetaError, dict[str, Any]]] = None
