"""
Quiz Service - Logic Candy Crush cho he thong quiz.

Logic chinh:
1. Level 1 (unlock_order=1): Luon mo san cho tat ca user
2. Level N mo khi level co unlock_order = N-1 dat >= 1 sao
3. Tinh sao: 0 sao (<50%), 1 sao (50-69%), 2 sao (70-89%), 3 sao (>=90%)
4. Cho lam lai nhieu lan, luu ky luc tot nhat
5. Cham diem tu dong theo loai cau hoi
"""
from datetime import datetime, timezone
import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import QuizAttempt, QuizLevel, QuizLevelProgress, QuizQuestion


# ==========================================
# EXCEPTIONS
# ==========================================

class QuizLevelNotFoundError(Exception):
    pass

class QuizLevelLockedError(Exception):
    pass

class QuizNoQuestionsError(Exception):
    pass


# ==========================================
# STAR CALCULATION
# ==========================================

def calculate_stars(score_percent: float) -> int:
    """
    Tinh so sao tu diem phan tram.
    
    - 0 sao: < 50%
    - 1 sao: 50% - 69%
    - 2 sao: 70% - 89%  
    - 3 sao: >= 90%
    """
    if score_percent >= 90:
        return 3
    elif score_percent >= 70:
        return 2
    elif score_percent >= 50:
        return 1
    return 0


# ==========================================
# ANSWER GRADING
# ==========================================

def grade_answer(question: QuizQuestion, user_answer) -> bool:
    """
    Cham diem 1 cau tra loi.
    
    Xu ly 4 loai cau hoi:
    - multiple_choice: So sanh option_id
    - fill_blank: So sanh danh sach tu dien vao
    - matching: So sanh cac cap ghep doi
    - ordering: So sanh thu tu sap xep
    """
    q_type = question.question_type
    interaction = question.interaction or {}
    
    if q_type == "multiple_choice":
        # User gui option_id (VD: "A", "B", "C")
        correct = question.correct_option_id
        if correct is None:
            return True  # Khong co dap an dung = free point
        user_str = str(user_answer).strip().upper()
        return user_str == correct.strip().upper()
    
    elif q_type == "fill_blank":
        # User gui list cac tu da dien
        sentence_answers = interaction.get("sentence_answers", [])
        if not sentence_answers:
            return True
        if not isinstance(user_answer, list):
            return False
        # So sanh tung tu (case-insensitive, trim)
        if len(user_answer) != len(sentence_answers):
            return False
        for ua, ca in zip(user_answer, sentence_answers):
            if str(ua).strip().lower() != str(ca).strip().lower():
                return False
        return True
    
    elif q_type == "matching":
        # User gui list cac cap {"left": ..., "right": ...}
        correct_pairs = interaction.get("pairs", [])
        if not correct_pairs:
            return True
        if not isinstance(user_answer, list):
            return False
        if len(user_answer) != len(correct_pairs):
            return False
        # Tao dict dap an dung
        correct_map = {}
        for p in correct_pairs:
            correct_map[str(p["left"]).strip().lower()] = str(p["right"]).strip().lower()
        # Kiem tra user
        for pair in user_answer:
            left = str(pair.get("left", "")).strip().lower()
            right = str(pair.get("right", "")).strip().lower()
            if correct_map.get(left) != right:
                return False
        return True
    
    elif q_type == "ordering":
        # User gui list thu tu da sap xep
        # BUG FIX: check ca 'sequence' (key cu) lan 'correct_sequence' (key moi)
        correct_sequence = interaction.get("correct_sequence") or interaction.get("sequence", [])
        if not correct_sequence:
            return True
        if not isinstance(user_answer, list):
            return False
        if len(user_answer) != len(correct_sequence):
            return False
        for ua, cs in zip(user_answer, correct_sequence):
            if str(ua).strip().lower() != str(cs).strip().lower():
                return False
        return True
    
    return False


# ==========================================
# QUIZ SERVICE
# ==========================================

class QuizService:
    """Service xu ly logic quiz kieu Candy Crush."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ------------------------------------------
    # GET LEVEL MAP (ban do cac man choi)
    # ------------------------------------------
    
    async def get_level_map(self, user_id: int) -> list[dict]:
        """
        Lay ban do tat ca levels voi tien do cua user.
        
        Logic mo khoa:
        - Level voi unlock_order=1: Luon is_unlocked=True
        - Level N: is_unlocked=True khi level (N-1) co stars >= 1
        """
        # Lay tat ca levels
        result = await self.db.execute(
            select(QuizLevel).order_by(QuizLevel.unlock_order)
        )
        levels = result.scalars().all()
        
        if not levels:
            return []
        
        # Lay progress cua user cho tat ca levels
        progress_result = await self.db.execute(
            select(QuizLevelProgress)
            .where(QuizLevelProgress.user_id == user_id)
        )
        progress_map: dict[int, QuizLevelProgress] = {}
        for p in progress_result.scalars().all():
            progress_map[p.level_id] = p
        
        # Build map voi logic unlock
        level_map = []
        prev_stars = 1  # Level dau tien luon mo
        
        for level in levels:
            progress = progress_map.get(level.id)
            
            # Logic unlock (chi dung de khoi tao progress record moi, KHONG override DB)
            if level.unlock_order == 1:
                calculated_unlock = True
            else:
                calculated_unlock = prev_stars >= 1
            
            # Tao hoac cap nhat progress record
            if progress:
                # BUG FIX: DB la nguon chan ly duy nhat truong is_unlocked
                # Chi update neu calculated=True MA db=False (khong bao gio lock lai)
                if calculated_unlock and not progress.is_unlocked:
                    progress.is_unlocked = True
                    self.db.add(progress)
                # Dung gia tri thuc trong DB
                is_unlocked = progress.is_unlocked
            else:
                # Tao progress record moi
                progress = QuizLevelProgress(
                    user_id=user_id,
                    level_id=level.id,
                    is_unlocked=calculated_unlock,
                    best_score=0.0,
                    stars=0,
                    attempts=0,
                )
                self.db.add(progress)
                progress_map[level.id] = progress
                is_unlocked = calculated_unlock
            
            stars = progress.stars if progress else 0
            best_score = progress.best_score if progress else 0.0
            attempt_count = progress.attempts if progress else 0
            
            level_map.append({
                "id": level.id,
                "file_id": level.file_id,
                "set_number": level.set_number,
                "set_title": level.set_title,
                "tags": level.tags if level.tags else [],
                "unlock_order": level.unlock_order,
                "is_unlocked": is_unlocked,  # Lay tu DB, khong phai tinh lai
                "stars": stars,
                "best_score": best_score,
                "attempt_count": attempt_count,
                "question_count": len(level.questions) if level.questions else 0,
            })
            
            prev_stars = stars
        
        await self.db.commit()
        return level_map

    
    # ------------------------------------------
    # GET LEVEL DETAIL (cau hoi de lam)
    # ------------------------------------------
    
    async def get_level_questions(self, user_id: int, level_id: int) -> dict:
        """
        Lay chi tiet level va danh sach cau hoi.
        
        - Kiem tra level co ton tai khong
        - Kiem tra user da mo khoa level chua
        - Tra ve cau hoi (KHONG tra dap an dung)
        """
        # Lay level
        result = await self.db.execute(
            select(QuizLevel).where(QuizLevel.id == level_id)
        )
        level = result.scalar_one_or_none()
        if not level:
            raise QuizLevelNotFoundError(f"Level {level_id} khong ton tai")
        
        # Kiem tra unlock
        progress = await self._get_or_create_progress(user_id, level)
        if not progress.is_unlocked:
            raise QuizLevelLockedError(
                f"Level '{level.set_title}' chua duoc mo khoa. "
                f"Hoan thanh level truoc do de mo khoa!"
            )
        
        # Lay cau hoi (sorted by order_index)
        questions = level.questions or []
        if not questions:
            raise QuizNoQuestionsError(f"Level '{level.set_title}' chua co cau hoi")
        
        questions_out = []
        for q in sorted(questions, key=lambda x: x.order_index):
            q_data = {
                "id": q.id,
                "question_id": q.question_id,
                "question_type": q.question_type,
                "prompt": q.prompt,
                "options": q.options if q.options else [],
                "interaction": q.interaction if q.interaction else {},
                "order_index": q.order_index,
                # Tra dap an dung de frontend hien thi feedback ngay lap tuc
                "correct_option_id": q.correct_option_id,
                "correct_option_text": q.correct_option_text,
            }
            # Xu ly interaction cho cac loai cau hoi tuong tac
            if q_data["interaction"]:
                safe_interaction = dict(q_data["interaction"])
                safe_interaction.pop("sentence_answers", None)  # Giu bi mat fill_blank
                if q.question_type == "matching":
                    pairs = safe_interaction.get("pairs", [])
                    lefts = [p["left"] for p in pairs]
                    rights = [p["right"] for p in pairs]
                    random.shuffle(rights)
                    safe_interaction["left_items"] = lefts
                    safe_interaction["right_items"] = rights
                    safe_interaction["correct_pairs"] = pairs  # De frontend check
                    safe_interaction.pop("pairs", None)
                if q.question_type == "ordering":
                    seq = safe_interaction.get("sequence", [])
                    shuffled = list(seq)
                    random.shuffle(shuffled)
                    safe_interaction["items_to_order"] = shuffled
                    # Giu sequence de frontend check
                    safe_interaction["correct_sequence"] = list(seq)
                    safe_interaction.pop("sequence", None)
                if q.question_type == "fill_blank":
                    # BUG-011 fix: fallback nhieu key khác nhau
                    bank = (
                        safe_interaction.get("bank")
                        or safe_interaction.get("word_bank")
                        or safe_interaction.get("words")
                        or []
                    )
                    bank = list(bank)  # make mutable copy
                    random.shuffle(bank)
                    safe_interaction["word_bank"] = bank
                    # Giu sentence_answers de frontend check
                    safe_interaction["sentence_answers"] = q.interaction.get("sentence_answers", [])
                q_data["interaction"] = safe_interaction
            questions_out.append(q_data)

        
        return {
            "id": level.id,
            "file_id": level.file_id,
            "set_number": level.set_number,
            "set_title": level.set_title,
            "tags": level.tags if level.tags else [],
            "questions": questions_out,
            "best_score": progress.best_score,
            "stars": progress.stars,
            "attempt_count": progress.attempts,
        }
    
    # ------------------------------------------
    # SUBMIT QUIZ (cham diem + cap nhat progress)
    # ------------------------------------------
    
    async def submit_quiz(
        self,
        user_id: int,
        level_id: int,
        answers: list[dict],
        duration_seconds: int | None = None,
    ) -> dict:
        """
        Nop bai quiz, cham diem, tinh sao, mo khoa level tiep theo.
        
        Logic:
        1. Cham tung cau hoi
        2. Tinh diem % = (so cau dung / tong cau) * 100
        3. Tinh sao tu diem %
        4. Cap nhat best_score va stars (chi cap nhat neu tot hon)
        5. Neu dat >= 1 sao, mo khoa level tiep theo
        """
        # Lay level
        result = await self.db.execute(
            select(QuizLevel).where(QuizLevel.id == level_id)
        )
        level = result.scalar_one_or_none()
        if not level:
            raise QuizLevelNotFoundError(f"Level {level_id} khong ton tai")
        
        # Kiem tra unlock
        progress = await self._get_or_create_progress(user_id, level)
        if not progress.is_unlocked:
            raise QuizLevelLockedError("Level chua duoc mo khoa!")
        
        # Lay tat ca cau hoi cua level
        questions = level.questions or []
        if not questions:
            raise QuizNoQuestionsError("Level chua co cau hoi")
        
        # Tao map question_id -> Question
        q_map: dict[str, QuizQuestion] = {}
        for q in questions:
            q_map[q.question_id] = q
        
        # Cham diem
        correct_count = 0
        total_questions = len(questions)
        answer_details = {}
        
        for ans in answers:
            qid = ans.get("question_id", "")
            user_answer = ans.get("answer")
            q = q_map.get(qid)
            
            if q:
                is_correct = grade_answer(q, user_answer)
                if is_correct:
                    correct_count += 1
                # Tra ve dap an dung de frontend highlight
                correct_answer = None
                if q.question_type == "multiple_choice":
                    correct_answer = q.correct_option_id
                elif q.question_type == "fill_blank":
                    correct_answer = (q.interaction or {}).get("sentence_answers", [])
                elif q.question_type == "matching":
                    correct_answer = (q.interaction or {}).get("pairs", [])
                elif q.question_type == "ordering":
                    correct_answer = (q.interaction or {}).get("sequence", [])
                answer_details[qid] = {
                    "answer": user_answer,
                    "correct": is_correct,
                    "correct_answer": correct_answer,
                }
        
        # Tinh diem va sao
        score_percent = (correct_count / total_questions * 100) if total_questions > 0 else 0
        stars = calculate_stars(score_percent)
        
        # Luu attempt
        attempt = QuizAttempt(
            user_id=user_id,
            level_id=level_id,
            score=round(score_percent, 1),
            stars=stars,
            correct_answers=correct_count,
            total_questions=total_questions,
            duration_seconds=duration_seconds,
            answers=answer_details,
        )
        self.db.add(attempt)
        
        # Cap nhat progress
        # BUG-010 fix: dung >= de is_new_best=True ca khi bang diem cu (consistent UX)
        is_new_best = score_percent >= progress.best_score and score_percent > 0
        progress.attempts += 1
        progress.last_played_at = datetime.now(timezone.utc)
        progress.last_attempted_at = datetime.now(timezone.utc)
        
        if is_new_best:
            progress.best_score = round(score_percent, 1)
        
        if stars > progress.stars:
            progress.stars = stars
        
        if progress.completed_at is None and stars >= 1:
            progress.completed_at = datetime.now(timezone.utc)
            progress.first_completed_at = datetime.now(timezone.utc)
            progress.is_completed = True
        
        self.db.add(progress)
        
        # Mo khoa level tiep theo neu dat >= 1 sao
        next_level_unlocked = False
        if stars >= 1:
            next_level_unlocked = await self._try_unlock_next(user_id, level)
        
        await self.db.commit()
        await self.db.refresh(attempt)
        
        # Tao message
        if stars == 3:
            message = "Tuyet voi! Ban dat 3 sao - Hoan hao!"
        elif stars == 2:
            message = "Rat gioi! Ban dat 2 sao. Thu lai de dat 3 sao nhe!"
        elif stars == 1:
            message = "Tot lam! Ban da qua man nay. Co the lam lai de cai thien!"
        else:
            message = "Chua dat yeu cau. Hay doc lai bai hoc va thu lai nhe!"
        
        return {
            "attempt_id": attempt.id,
            "level_id": level_id,
            "score": round(score_percent, 1),
            "stars": stars,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "is_new_best": is_new_best,
            "next_level_unlocked": next_level_unlocked,
            "answer_details": answer_details,  # {qid: {answer, correct, correct_answer}}
            "message": message,
        }
    
    # ------------------------------------------
    # GET OVERALL PROGRESS
    # ------------------------------------------
    
    async def get_overall_progress(self, user_id: int) -> dict:
        """
        Lay tong quan tien do quiz cua user.
        """
        # Dem tong levels
        total_result = await self.db.execute(
            select(func.count(QuizLevel.id))
        )
        total_levels = total_result.scalar() or 0
        
        # Dem levels da hoan thanh (>= 1 sao)
        completed_result = await self.db.execute(
            select(func.count(QuizLevelProgress.id))
            .where(
                QuizLevelProgress.user_id == user_id,
                QuizLevelProgress.stars >= 1,
            )
        )
        completed_levels = completed_result.scalar() or 0
        
        # Tong sao
        stars_result = await self.db.execute(
            select(func.coalesce(func.sum(QuizLevelProgress.stars), 0))
            .where(QuizLevelProgress.user_id == user_id)
        )
        total_stars = stars_result.scalar() or 0
        
        max_possible = total_levels * 3
        completion = (completed_levels / total_levels * 100) if total_levels > 0 else 0
        
        return {
            "total_levels": total_levels,
            "completed_levels": completed_levels,
            "total_stars": total_stars,
            "max_possible_stars": max_possible,
            "completion_percent": round(completion, 1),
        }
    
    # ------------------------------------------
    # HELPERS
    # ------------------------------------------
    
    async def _get_or_create_progress(
        self, user_id: int, level: QuizLevel
    ) -> QuizLevelProgress:
        """Lay hoac tao progress record cho user + level."""
        result = await self.db.execute(
            select(QuizLevelProgress)
            .where(
                QuizLevelProgress.user_id == user_id,
                QuizLevelProgress.level_id == level.id,
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            is_unlocked = level.unlock_order == 1  # Level dau tien luon mo
            progress = QuizLevelProgress(
                user_id=user_id,
                level_id=level.id,
                is_unlocked=is_unlocked,
                best_score=0.0,
                stars=0,
                attempts=0,
            )
            self.db.add(progress)
            await self.db.flush()
        
        return progress
    
    async def _try_unlock_next(self, user_id: int, current_level: QuizLevel) -> bool:
        """
        Mo khoa level tiep theo.
        
        BUG FIX: Dung '>current_order ORDER BY ASC LIMIT 1' thay vi '== +1'
        de handle truong hop gap trong unlock_order.
        Returns True neu da mo khoa duoc.
        """
        # Tim level co unlock_order nho nhat MA LON HON current
        result = await self.db.execute(
            select(QuizLevel)
            .where(QuizLevel.unlock_order > current_level.unlock_order)
            .order_by(QuizLevel.unlock_order)
            .limit(1)
        )
        next_level = result.scalar_one_or_none()
        
        if not next_level:
            return False  # Da la level cuoi
        
        # Kiem tra xem da co progress chua
        result = await self.db.execute(
            select(QuizLevelProgress)
            .where(
                QuizLevelProgress.user_id == user_id,
                QuizLevelProgress.level_id == next_level.id,
            )
        )
        next_progress = result.scalar_one_or_none()
        
        if next_progress:
            if next_progress.is_unlocked:
                return False  # Da mo roi, tra False nhung khong phai loi
            next_progress.is_unlocked = True
            self.db.add(next_progress)
        else:
            next_progress = QuizLevelProgress(
                user_id=user_id,
                level_id=next_level.id,
                is_unlocked=True,
                best_score=0.0,
                stars=0,
                attempts=0,
            )
            self.db.add(next_progress)
        
        return True
