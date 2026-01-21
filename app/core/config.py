"""
Cau hinh ung dung Calmi.
Doc cac bien moi truong tu file .env va cung cap cho toan bo ung dung.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Lop chua toan bo cau hinh cua ung dung.
    Cac gia tri duoc doc tu bien moi truong hoac file .env
    """
    
    # Cau hinh database
    DATABASE_URL: str
    
    # Cau hinh ung dung
    APP_NAME: str = "Calmi"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Cau hinh bao mat va JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_HOURS: int = 24
    
    # Cau hinh CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    
    # Cau hinh Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Calmi <onboarding@resend.dev>"
    EMAIL_ENABLED: bool = False
    
    # Cau hinh OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-nano"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Tra ve danh sach cac origin duoc phep truy cap."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """
    Lay instance Settings (cached).
    Su dung lru_cache de chi doc file .env mot lan.
    """
    return Settings()
