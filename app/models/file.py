"""
Model File - Quan ly file upload va Identity Firewall.
Ho tro luu tru file goc va file da an danh hoa.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class File(Base, TimestampMixin):
    """
    Bang files - Luu tru thong tin file upload.
    
    Ho tro Identity Firewall:
    - storage_path: Duong dan file goc
    - anonymized_path: Duong dan file da xoa metadata
    - is_anonymized: Trang thai da an danh hoa
    
    Attributes:
        id: Khoa chinh
        owner_user_id: Nguoi upload file
        storage_path: Duong dan luu tru file goc
        original_filename: Ten file goc
        mime_type: Loai file (image/jpeg, application/pdf, ...)
        size_bytes: Kich thuoc file (bytes)
        is_anonymized: Da xoa metadata chua
        anonymized_path: Duong dan file da an danh hoa
        checksum: Ma bam de kiem tra toan ven
    """
    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anonymized_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Relationships
    owner: Mapped["User | None"] = relationship(
        "User",
        back_populates="files",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename='{self.original_filename}')>"
