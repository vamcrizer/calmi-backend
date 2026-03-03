"""
Cache Warm-up Script - Goi tat ca API endpoints truoc khi demo.

Su dung: python warmup_cache.py
  - Tu dong login va goi tat ca GET endpoints
  - Lap day cache phia server -> lan goi tiep theo se nhanh (<10ms)
  - Nen chay 30-60 giay truoc khi demo

Ket hop voi benchmark: 
  python warmup_cache.py && python benchmark_api.py --save after_warmup --compare benchmarks/bench_XXXXX_baseline.json
"""
import asyncio
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
CREDENTIALS = {"identifier": "student01", "password": "Calmi123!@#"}

# Tat ca GET endpoints can warm up
WARMUP_ENDPOINTS = [
    # Auth
    "/api/v1/auth/me",
    # Moods  
    "/api/v1/moods/my",
    "/api/v1/moods/stats?days=7",
    "/api/v1/moods/streak",
    "/api/v1/moods/ai-summary",
    # Chat
    "/api/v1/chat/sessions",
    # Education
    "/api/v1/education/contents",
    "/api/v1/education/daily-kind-message",
    "/api/v1/education/my/history",
    # Reports
    "/api/v1/reports/incident-types",
    "/api/v1/reports/my",
    # Quiz
    "/api/v1/quiz/levels",
    "/api/v1/quiz/progress",
]


async def main():
    print("=" * 60)
    print("  CALMI CACHE WARM-UP")
    print("=" * 60)
    
    total_start = time.perf_counter()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        print("\n1. Dang nhap...")
        try:
            resp = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=CREDENTIALS,
            )
            resp.raise_for_status()
            token = resp.json()["data"]["access_token"]
            print(f"   OK ({(time.perf_counter() - total_start)*1000:.0f}ms)")
        except Exception as e:
            print(f"   LOI: {e}")
            print("\n   Kiem tra backend dang chay chua!")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Goi tat ca endpoints (lan 1 - lap day cache)
        print(f"\n2. Warm-up {len(WARMUP_ENDPOINTS)} endpoints (lan 1 - cham)...")
        for path in WARMUP_ENDPOINTS:
            start = time.perf_counter()
            try:
                resp = await client.get(f"{BASE_URL}{path}", headers=headers)
                ms = (time.perf_counter() - start) * 1000
                icon = "OK" if resp.status_code < 400 else "!!"
                print(f"   [{icon}] {path:<45} {ms:>7.0f}ms")
            except Exception as e:
                ms = (time.perf_counter() - start) * 1000
                print(f"   [ER] {path:<45} {ms:>7.0f}ms  {e}")
        
        # 3. Kiem tra cache (lan 2 - phai nhanh)
        print(f"\n3. Verify cache (lan 2 - phai nhanh)...")
        fast_count = 0
        for path in WARMUP_ENDPOINTS:
            start = time.perf_counter()
            try:
                resp = await client.get(f"{BASE_URL}{path}", headers=headers)
                ms = (time.perf_counter() - start) * 1000
                is_fast = ms < 100
                icon = "FAST" if is_fast else "SLOW"
                if is_fast:
                    fast_count += 1
                print(f"   [{icon}] {path:<45} {ms:>7.0f}ms")
            except Exception as e:
                print(f"   [ER]  {path:<45} {e}")
    
    total_ms = (time.perf_counter() - total_start) * 1000
    
    print(f"\n{'=' * 60}")
    print(f"  HOAN THANH trong {total_ms/1000:.1f}s")
    print(f"  Cache hit: {fast_count}/{len(WARMUP_ENDPOINTS)} endpoints nhanh (<100ms)")
    print(f"  San sang demo!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    # Fix Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    
    asyncio.run(main())
