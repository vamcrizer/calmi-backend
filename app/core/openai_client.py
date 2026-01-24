"""
Shared OpenAI client with connection pooling.
Reuses connections across requests for better performance.

OPTIMIZED: Single client instance with httpx connection pool.
"""
from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

# Shared httpx client with connection pooling
_http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,  # Keep 20 connections alive
        max_connections=50,  # Max 50 concurrent connections
        keepalive_expiry=30.0,  # Keep connections for 30s
    ),
    timeout=httpx.Timeout(
        connect=5.0,  # 5s to connect
        read=60.0,  # 60s to read (for streaming)
        write=10.0,  # 10s to write
        pool=10.0,  # 10s to get connection from pool
    ),
)


@lru_cache(maxsize=1)
def get_async_openai_client() -> AsyncOpenAI:
    """
    Get shared AsyncOpenAI client (cached singleton).
    
    Uses connection pooling for faster subsequent requests.
    """
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=_http_client,
        max_retries=2,
        timeout=30.0,
    )


# Convenience function for chat completions
async def quick_chat_completion(
    messages: list[dict],
    model: str = None,
    max_tokens: int = 500,
    response_format: dict = None,
) -> str:
    """
    Quick helper for simple chat completions.
    Uses shared client for connection reuse.
    """
    client = get_async_openai_client()
    
    kwargs = {
        "model": model or settings.OPENAI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
