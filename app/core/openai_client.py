"""
Shared OpenAI client with connection pooling and HTTP/2 support.
Reuses connections across requests for better performance on slow networks.

OPTIMIZED: HTTP/2 multiplexing, aggressive keepalive, reduced timeouts.
"""
from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

# OPTIMIZED: Shared httpx client with HTTP/2 support
_http_client = httpx.AsyncClient(
    http2=True,  # Enable HTTP/2 for multiplexed connections
    limits=httpx.Limits(
        max_keepalive_connections=30,  # More keepalive connections
        max_connections=100,  # More concurrent connections
        keepalive_expiry=60.0,  # Keep connections longer (60s)
    ),
    timeout=httpx.Timeout(
        connect=3.0,  # Faster connect timeout (3s)
        read=45.0,  # Read timeout for streaming
        write=5.0,  # Faster write timeout
        pool=5.0,  # Faster pool timeout
    ),
)


@lru_cache(maxsize=1)
def get_async_openai_client() -> AsyncOpenAI:
    """
    Get shared AsyncOpenAI client (cached singleton).
    
    Uses HTTP/2 and connection pooling for faster subsequent requests.
    """
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=_http_client,
        max_retries=2,
        timeout=25.0,  # Reduced timeout
    )


async def quick_chat_completion(
    messages: list[dict],
    model: str = None,
    max_tokens: int = 300,  # Reduced default
    response_format: dict = None,
    stream: bool = False,
) -> str:
    """
    Quick helper for simple chat completions.
    Uses shared client for connection reuse.
    
    For streaming, set stream=True and iterate over result.
    """
    client = get_async_openai_client()
    
    kwargs = {
        "model": model or settings.OPENAI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    if stream:
        # Return async generator for streaming
        return await client.chat.completions.create(**kwargs)
    else:
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

