"""
API Timing Middleware - Đo thời gian xử lý của mọi request.

Thêm header X-Process-Time vào response và log các request chậm.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.timing")

# Ngưỡng cảnh báo (ms)
SLOW_THRESHOLD_MS = 1000  # > 1s = chậm
VERY_SLOW_THRESHOLD_MS = 3000  # > 3s = rất chậm


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware đo thời gian xử lý request.
    
    - Thêm header `X-Process-Time` (ms) vào mọi response
    - Log warning cho request chậm (> 1s)
    - Log error cho request rất chậm (> 3s)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Thêm header timing
        response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"
        
        # Log theo mức độ
        path = request.url.path
        method = request.method
        status = response.status_code
        
        if duration_ms >= VERY_SLOW_THRESHOLD_MS:
            logger.error(
                f"🔴 VERY SLOW | {method} {path} | {status} | {duration_ms:.0f}ms"
            )
        elif duration_ms >= SLOW_THRESHOLD_MS:
            logger.warning(
                f"🟡 SLOW | {method} {path} | {status} | {duration_ms:.0f}ms"
            )
        else:
            # Chỉ log API calls, bỏ qua static files
            if path.startswith("/api/"):
                logger.info(
                    f"🟢 OK | {method} {path} | {status} | {duration_ms:.0f}ms"
                )
        
        return response
