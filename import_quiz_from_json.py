"""
Import Quiz Data tu file1.json vao PostgreSQL.

Usage:
    python import_quiz_from_json.py [--json-file file1.json] [--dry-run]

- Xoa toan bo quiz_questions va quiz_levels cu
- Insert moi tu file JSON
- Giu nguyen quiz_attempts va quiz_level_progress
"""
import asyncio
import json
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load .env
from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()


async def import_quiz(json_file: str = "file1.json", dry_run: bool = False):
    print("=" * 60)
    print("  IMPORT QUIZ DATA tu JSON -> PostgreSQL")
    print("=" * 60)

    # Load JSON
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"[ERR] Khong tim thay file: {json_file}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    files = data.get("files", [])
    print(f"\n[INFO] Tim thay {len(files)} bo quiz trong {json_file}")

    # Ket noi DB
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # 1. Kiem tra so luong data hien tai
        result = await db.execute(sa.text("SELECT COUNT(*) FROM quiz_levels"))
        old_levels = result.scalar()
        result = await db.execute(sa.text("SELECT COUNT(*) FROM quiz_questions"))
        old_questions = result.scalar()
        print(f"\n[DB] Hien tai: {old_levels} levels, {old_questions} questions")

        # 2. Xac nhan
        if not dry_run:
            print(f"\n[!] Se XOA toan bo {old_levels} levels va {old_questions} questions")
            print(f"    (quiz_attempts va quiz_level_progress duoc GIU NGUYEN)")
            confirm = input("    Tiep tuc? (y/N): ").strip().lower()
            if confirm != "y":
                print("    Huy bo.")
                return

        total_levels = 0
        total_questions = 0

        if dry_run:
            print("\n[DRY-RUN] Khong ghi vao DB, chi kiem tra format...")
        else:
            # 3. Xoa data cu (cascade xoa quiz_questions)
            await db.execute(sa.text("DELETE FROM quiz_questions"))
            await db.execute(sa.text("DELETE FROM quiz_levels"))
            await db.commit()
            print("\n[OK] Da xoa data cu")

        # 4. Insert moi
        for file_index, file_data in enumerate(files):
            file_id = file_data["file_id"]
            set_number = file_data["set_number"]
            set_title = file_data["set_title"]
            tags = json.dumps(file_data.get("tags", []), ensure_ascii=False)
            questions = file_data.get("questions", [])
            unlock_order = file_index + 1  # Sequential, unique

            print(f"\n  [{file_id}] {set_title} ({len(questions)} cau)")

            if not dry_run:
                # Insert quiz_level
                result = await db.execute(
                    sa.text("""
                        INSERT INTO quiz_levels (file_id, set_number, set_title, tags, is_active, unlock_order)
                        VALUES (:file_id, :set_number, :set_title, CAST(:tags AS jsonb), true, :unlock_order)
                        RETURNING id
                    """),
                    {
                        "file_id": file_id,
                        "set_number": set_number,
                        "set_title": set_title,
                        "tags": tags,
                        "unlock_order": unlock_order,
                    }
                )
                level_id = result.scalar()
            else:
                level_id = 0

            total_levels += 1

            # Insert questions
            for order_idx, q in enumerate(questions):
                question_id = q["question_id"]
                question_type = q["question_type"]
                prompt = q["prompt"]
                options = json.dumps(q.get("options", []), ensure_ascii=False)
                correct_option_id = q.get("correct_option_id")
                correct_option_text = q.get("correct_option_text")
                explanation = q.get("explanation")
                interaction = json.dumps(q.get("interaction", {}), ensure_ascii=False)

                print(f"    [{question_id}] {question_type}: {prompt[:40]}...")

                if not dry_run:
                    await db.execute(
                        sa.text("""
                            INSERT INTO quiz_questions (
                                level_id, question_id, question_type, prompt,
                                options, correct_option_id, correct_option_text,
                                explanation, interaction, order_index
                            ) VALUES (
                                :level_id, :question_id, :question_type, :prompt,
                                CAST(:options AS jsonb), :correct_option_id, :correct_option_text,
                                :explanation, CAST(:interaction AS jsonb), :order_index
                            )
                        """),
                        {
                            "level_id": level_id,
                            "question_id": question_id,
                            "question_type": question_type,
                            "prompt": prompt,
                            "options": options,
                            "correct_option_id": correct_option_id,
                            "correct_option_text": correct_option_text,
                            "explanation": explanation,
                            "interaction": interaction,
                            "order_index": order_idx,
                        }
                    )

                total_questions += 1

        if not dry_run:
            await db.commit()

        # 5. Ket qua
        print(f"\n{'=' * 60}")
        if dry_run:
            print(f"  [DRY-RUN] Se import: {total_levels} levels, {total_questions} questions")
        else:
            # Verify
            result = await db.execute(sa.text("SELECT COUNT(*) FROM quiz_levels"))
            new_levels = result.scalar()
            result = await db.execute(sa.text("SELECT COUNT(*) FROM quiz_questions"))
            new_questions = result.scalar()
            print(f"  [OK] HOAN THANH!")
            print(f"  Quiz Levels : {new_levels}")
            print(f"  Questions   : {new_questions}")

            # Hien thi summary
            result = await db.execute(sa.text(
                "SELECT file_id, set_title, (SELECT COUNT(*) FROM quiz_questions WHERE level_id = ql.id) as q_count "
                "FROM quiz_levels ql ORDER BY set_number"
            ))
            print(f"\n  {'File ID':<10} {'Set Title':<35} {'Questions'}")
            print(f"  {'-'*10} {'-'*35} {'-'*9}")
            for row in result.fetchall():
                print(f"  {row[0]:<10} {row[1]:<35} {row[2]}")

        print(f"{'=' * 60}")

    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Import quiz data from JSON to PostgreSQL")
    parser.add_argument("--json-file", default="file1.json", help="Path to JSON file (default: file1.json)")
    parser.add_argument("--dry-run", action="store_true", help="Chi kiem tra, khong ghi vao DB")
    args = parser.parse_args()

    asyncio.run(import_quiz(args.json_file, args.dry_run))
