"""
Calmi - Ung dung FastAPI chinh.
Entry point cua ung dung backend.

OPTIMIZED: GZip compression and connection pool warmup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.schemas.common import api_response

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quan ly vong doi cua ung dung.
    - Khoi tao ket noi database khi startup
    - Warm up connection pools
    - Don dep khi shutdown
    """
    # Startup
    print(f"[Calmi] Khoi dong ung dung {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # OPTIMIZED: Warm up OpenAI connection pool
    try:
        from app.core.openai_client import get_async_openai_client
        client = get_async_openai_client()
        print("[Calmi] ✓ OpenAI client initialized with connection pool")
    except Exception as e:
        print(f"[Calmi] ⚠ OpenAI client warmup failed: {e}")
    
    yield
    
    # Shutdown
    print("[Calmi] Dong ung dung")


def create_app() -> FastAPI:
    """
    Factory function tao FastAPI app.
    
    Returns:
        FastAPI app instance da cau hinh
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API cho nen tang an toan hoc duong Calmi",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # OPTIMIZED: GZip compression for smaller payload sizes
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # Cau hinh CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Dang ky API routers
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Kiem tra trang thai he thong."""
        return api_response(
            data={
                "status": "healthy",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
            },
            message="He thong hoat dong binh thuong",
        )
    
    return app


# Tao app instance
app = create_app()

