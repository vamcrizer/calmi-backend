"""
Schemas cho Role - Dinh nghia cac Pydantic model cho API.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """Schema co so cho Role."""
    code: str = Field(..., max_length=50, description="Ma vai tro")
    name: str = Field(..., max_length=255, description="Ten vai tro")
    description: str | None = Field(None, description="Mo ta vai tro")


class RoleCreate(RoleBase):
    """Schema de tao moi Role."""
    pass


class RoleUpdate(BaseModel):
    """Schema de cap nhat Role."""
    code: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    description: str | None = None


class RoleRead(RoleBase):
    """Schema tra ve khi doc Role."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
