"""
Schemas chung, pagination va API response wrapper.
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    Tat ca API endpoints se tra ve response theo format nay.
    
    Attributes:
        status_code: HTTP status code
        success: True neu thanh cong, False neu loi
        data: Du lieu tra ve (generic type)
        message: Thong bao cho nguoi dung
    """
    status_code: int = Field(200, description="HTTP status code")
    success: bool = Field(True, description="True neu thanh cong")
    data: T | None = Field(None, description="Du lieu tra ve")
    message: str = Field("", description="Thong bao")
    
    class Config:
        from_attributes = True


class ApiListResponse(BaseModel, Generic[T]):
    """
    API response wrapper cho danh sach.
    
    Attributes:
        status_code: HTTP status code
        success: True neu thanh cong
        data: Danh sach items
        message: Thong bao
        total: Tong so items (cho pagination)
    """
    status_code: int = Field(200, description="HTTP status code")
    success: bool = Field(True, description="True neu thanh cong")
    data: list[T] = Field(default_factory=list, description="Danh sach items")
    message: str = Field("", description="Thong bao")
    total: int | None = Field(None, description="Tong so items")


class PaginationParams(BaseModel):
    """Tham so phan trang."""
    skip: int = Field(0, ge=0, description="So ban ghi bo qua")
    limit: int = Field(20, ge=1, le=100, description="So ban ghi toi da")


class PaginatedResponse(BaseModel, Generic[T]):
    """Response co phan trang."""
    items: list[T]
    total: int
    skip: int
    limit: int
    
    @property
    def has_more(self) -> bool:
        """Kiem tra con du lieu khong."""
        return self.skip + len(self.items) < self.total


class MessageResponse(BaseModel):
    """Response don gian chi chua message."""
    message: str
    success: bool = True


# Helper functions de tao response
def api_response(
    data: Any = None,
    message: str = "",
    status_code: int = 200,
    success: bool = True,
) -> dict:
    """
    Tao API response dict.
    
    Args:
        data: Du lieu tra ve
        message: Thong bao
        status_code: HTTP status code
        success: True neu thanh cong
        
    Returns:
        Dict theo format ApiResponse
    """
    return {
        "status_code": status_code,
        "success": success,
        "data": data,
        "message": message,
    }


def api_list_response(
    data: list,
    message: str = "",
    total: int | None = None,
    status_code: int = 200,
) -> dict:
    """
    Tao API list response dict.
    
    Args:
        data: Danh sach items
        message: Thong bao
        total: Tong so items
        status_code: HTTP status code
        
    Returns:
        Dict theo format ApiListResponse
    """
    return {
        "status_code": status_code,
        "success": True,
        "data": data,
        "message": message,
        "total": total if total is not None else len(data),
    }


def api_error(
    message: str,
    status_code: int = 400,
    data: Any = None,
) -> dict:
    """
    Tao API error response dict.
    
    Args:
        message: Thong bao loi
        status_code: HTTP status code
        data: Du lieu bo sung (optional)
        
    Returns:
        Dict theo format ApiResponse voi success=False
    """
    return {
        "status_code": status_code,
        "success": False,
        "data": data,
        "message": message,
    }

