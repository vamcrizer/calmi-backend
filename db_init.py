#!/usr/bin/env python
"""
db_init.py — CLI script để khởi tạo database Calmi.

Usage:
    python db_init.py              # Setup schema + seed
    python db_init.py --schema     # Chỉ chạy setup.sql
    python db_init.py --seed       # Chỉ chạy seed.sql
    python db_init.py --quiz       # Import quiz từ file1.json
    python db_init.py --reset      # DROP tất cả rồi setup lại (nguy hiểm!)
    python db_init.py --check      # Kiểm tra kết nối và in thống kê

Cấu hình: đọc DATABASE_URL từ .env hoặc biến môi trường.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── load .env ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv không bắt buộc nếu dùng env var thật

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_DIR = Path(__file__).parent / "db"

# ── colours ──────────────────────────────────────────────────
def green(s):  return f"\033[92m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"
def ok(s):     return f"[OK] {s}"
def fail(s):   return f"[FAIL] {s}"


# ── helpers ──────────────────────────────────────────────────

def get_psql_url(db_url: str) -> str:
    """Chuyển asyncpg URL sang psql-compatible URL."""
    return db_url.replace("postgresql+asyncpg://", "postgresql://")


async def run_sql_file(sql_file: Path, label: str):
    """Chạy file SQL bằng asyncpg trực tiếp (không cần psql binary)."""
    import asyncpg

    # Parse connection string
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    print(f"\n{bold(f'▶ {label}')}  ({sql_file.name})")
    sql = sql_file.read_text(encoding="utf-8")

    conn = await asyncpg.connect(url)
    try:
        # asyncpg không chạy được nhiều statements cùng lúc qua execute()
        # → dùng executemany + tách statement
        await conn.execute(sql)
        print(green(f"  [OK] {label} thanh cong"))
    except Exception as e:
        print(red(f"  [FAIL] {label} that bai: {e}"))
        raise
    finally:
        await conn.close()


async def run_schema():
    await run_sql_file(DB_DIR / "setup.sql", "Tạo schema (setup.sql)")


async def run_seed():
    await run_sql_file(DB_DIR / "seed.sql", "Seed dữ liệu (seed.sql)")


async def run_quiz_import():
    """Import quiz data từ file1.json."""
    import subprocess
    print(f"\n{bold('▶ Import quiz data')}  (import_quiz_from_json.py)")
    script = Path(__file__).parent / "import_quiz_from_json.py"
    if not script.exists():
        print(yellow("  import_quiz_from_json.py không tồn tại, bỏ qua."))
        return
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(green("  [OK] Import quiz thanh cong"))
        if result.stdout:
            print(result.stdout[-500:])  # last 500 chars
    else:
        print(red("  [FAIL] Import quiz that bai"))
        print(result.stderr[-500:])
        raise RuntimeError("Quiz import failed")


async def run_check():
    """Kiểm tra kết nối và in thống kê."""
    import asyncpg
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    print(f"\n{bold('▶ Kiểm tra kết nối')}")
    conn = await asyncpg.connect(url)
    try:
        tables = [
            "schools", "roles", "users", "classes",
            "quiz_levels", "quiz_questions", "quiz_level_progress",
            "chat_sessions", "mood_entries", "reports",
        ]
        print(f"\n{'Bảng':<30} {'Số dòng':>10}")
        print("─" * 42)
        for tbl in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {tbl}")
                print(f"  {tbl:<28} {count:>10}")
            except Exception:
                print(f"  {tbl:<28} {'(chưa tạo)':>10}")
        print(green("\n  [OK] Ket noi OK"))
    finally:
        await conn.close()


async def run_reset():
    """DROP PUBLIC SCHEMA và tạo lại."""
    import asyncpg
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    print(red("\n  [!] Reset: se XOA TOAN BO DU LIEU!"))
    confirm = input("  Gõ 'yes' để xác nhận: ").strip().lower()
    if confirm != "yes":
        print("  Huỷ.")
        return

    conn = await asyncpg.connect(url)
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        print(green("  [OK] Da reset schema"))
    finally:
        await conn.close()

    await run_schema()
    await run_seed()
    await run_quiz_import()


# ── main ─────────────────────────────────────────────────────

async def main():
    if not DATABASE_URL:
        print(red("❌ Thiếu DATABASE_URL. Kiểm tra file .env"))
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Calmi DB Init — khởi tạo database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--schema", action="store_true", help="Chỉ chạy setup.sql")
    parser.add_argument("--seed",   action="store_true", help="Chỉ chạy seed.sql")
    parser.add_argument("--quiz",   action="store_true", help="Chỉ import quiz")
    parser.add_argument("--reset",  action="store_true", help="DROP rồi setup lại")
    parser.add_argument("--check",  action="store_true", help="Kiểm tra kết nối")
    args = parser.parse_args()

    print(bold("\n🚀 Calmi DB Init"))
    masked = DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL
    print(f"   DB: {masked}\n")

    try:
        if args.reset:
            await run_reset()
        elif args.schema:
            await run_schema()
        elif args.seed:
            await run_seed()
        elif args.quiz:
            await run_quiz_import()
        elif args.check:
            await run_check()
        else:
            # Mặc định: chạy tất cả
            await run_schema()
            await run_seed()
            await run_quiz_import()
            await run_check()

        print(bold(green("\n[DONE]\n")))

    except Exception as e:
        print(red(f"\n[ERROR]: {e}\n"))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
