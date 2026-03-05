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
        print("[Calmi] [OK] OpenAI client initialized with connection pool")
    except Exception as e:
        print(f"[Calmi] [WARN] OpenAI client warmup failed: {e}")
    
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
    
    # NOTE: FastAPI applies middleware in REVERSE order of add_middleware calls.
    # So the LAST middleware added runs FIRST on incoming requests.
    # CORS must be added LAST to ensure it runs FIRST and always sets CORS headers,
    # even when other middleware or endpoints raise 500 errors.

    # 1. GZip - runs last (innermost)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # 2. Timing middleware - runs second
    from app.middleware.timing import TimingMiddleware
    app.add_middleware(TimingMiddleware)
    
    # 3. CORS - runs first (outermost), always sets Access-Control-Allow-Origin
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    # Them origins tu .env neu co
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        import json
        try:
            env_origins = json.loads(settings.CORS_ORIGINS) if isinstance(settings.CORS_ORIGINS, str) else settings.CORS_ORIGINS
            cors_origins.extend([o for o in env_origins if o not in cors_origins])
        except Exception:
            pass
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
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
    
    @app.get("/cache-stats", tags=["Health"])
    async def cache_stats():
        """Xem thong ke cache (hit rate, size, etc)."""
        from app.core.cache import cache
        return api_response(data=cache.stats())
    
    @app.delete("/cache-clear", tags=["Health"])
    async def cache_clear():
        """Xoa toan bo cache (dung khi debug)."""
        from app.core.cache import cache
        cache.clear()
        return api_response(data={"cleared": True})
    
    return app


# Tao app instance
app = create_app()

