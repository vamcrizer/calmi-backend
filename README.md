# Calmi Backend

FastAPI backend cho hệ thống hỗ trợ sức khỏe tâm thần học đường (AI Chatbot, Quiz, Báo cáo).

## Yêu cầu

- Python 3.11+
- PostgreSQL 15+ (hoặc Supabase)
- OpenAI API key

---

## Cài đặt nhanh

### 1. Clone & cài dependencies

```bash
git clone <repo>
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Cấu hình môi trường

```bash
cp .env.example .env
```

Chỉnh `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/calmi
SECRET_KEY=your-secret-key-min-32-chars
OPENAI_API_KEY=sk-...
```

> Xem `.env.example` để biết đầy đủ các biến.

### 3. Khởi tạo database

Tạo database trống trước (1 lần duy nhất):
```bash
createdb calmi   # hoặc tạo trong Supabase
```

Sau đó dùng CLI script — **không cần pgAdmin, không cần cài psql**:

```bash
# Chạy tất cả (schema + seed + quiz) — dùng lần đầu
python db_init.py

# Hoặc từng bước
python db_init.py --schema   # Tạo bảng
python db_init.py --seed     # Chèn dữ liệu mẫu
python db_init.py --quiz     # Import quiz từ file1.json
python db_init.py --check    # Kiểm tra kết nối
python db_init.py --reset    # ⚠️ Xoá sạch rồi setup lại
```

> **Supabase**: Vào SQL Editor → paste `db/setup.sql` → Run, rồi chạy `python db_init.py --seed --quiz`.

**Tài khoản demo** (password: `Password123!`):

| Username | Vai trò |
|----------|--------|
| `student01` | Học sinh |
| `student02` | Học sinh |
| `teacher01` | Giáo viên |
| `counselor01` | Tham vấn viên |
| `admin01` | Quản trị trường |

### 4. Chạy server

```bash
python run.py
# hoặc
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

## Cấu trúc project

```
backend/
├── app/
│   ├── api/v1/          # Endpoints (auth, chat, quiz, reports...)
│   ├── core/            # Config, database, cache, security
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # DB queries
│   ├── schemas/         # Pydantic schemas
│   └── services/        # Business logic
├── db/
│   ├── setup.sql        # Schema đầy đủ (tất cả bảng)
│   ├── seed.sql         # Dữ liệu demo
│   └── seed_*.sql       # Seed phụ
├── db_init.py           # ← CLI khởi tạo DB
├── file1.json           # Dữ liệu quiz nguồn
├── import_quiz_from_json.py
├── .env.example
├── requirements.txt
└── Dockerfile
```

---

## Database Schema

11 module chính (xem `db/setup.sql`):

| Module | Tables |
|--------|--------|
| Core | `schools`, `roles`, `users`, `student_profiles`, `teacher_profiles` |
| Auth | `auth_refresh_tokens`, `password_reset_tokens` |
| Education | `classes`, `education_contents`, `exercise_questions`, `exercise_attempts` |
| Mood | `mood_entries` |
| Chat | `chat_sessions`, `chat_messages` |
| Reports | `incident_types`, `reports`, `report_attachments`, `report_status_history`, `report_ai_analyses` |
| Quiz | `quiz_levels`, `quiz_questions`, `quiz_level_progress`, `quiz_attempts` |
| Misc | `files`, `notifications`, `system_settings` |

---

## Biến môi trường

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` |
| `SECRET_KEY` | ✅ | JWT secret (≥32 ký tự) |
| `OPENAI_API_KEY` | ✅ | Cho AI chatbot |
| `OPENAI_MODEL` | | Default: `gpt-4.1-nano` |
| `CORS_ORIGINS` | | Default: `http://localhost:3000` |
| `RESEND_API_KEY` | | Cho tính năng email |
| `EMAIL_ENABLED` | | `false` để tắt email |

---

## Docker

```bash
docker compose up -d
```

---

## Deploy

Xem `DEPLOYMENT_WORKFLOW.md` và `CICD_SETUP.md`.
