-- =============================================================
-- CALMI BACKEND — COMPLETE DATABASE SETUP
-- PostgreSQL 15+
-- Run once on a fresh database to set up all tables.
-- =============================================================

-- =============================================================
-- MODULE 1: CORE — schools, roles, users
-- =============================================================

CREATE TABLE IF NOT EXISTS schools (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    code        VARCHAR(50) UNIQUE,
    address     TEXT,
    province    VARCHAR(100),
    district    VARCHAR(100),
    phone       VARCHAR(50),
    email       VARCHAR(255),
    status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, INACTIVE
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roles (
    id          BIGSERIAL PRIMARY KEY,
    code        VARCHAR(50) NOT NULL UNIQUE,  -- STUDENT, TEACHER, COUNSELOR, SCHOOL_ADMIN, SYSTEM_ADMIN
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default roles
INSERT INTO roles (code, name, description) VALUES
    ('STUDENT',      'Học sinh',            'Học sinh phổ thông'),
    ('TEACHER',      'Giáo viên',           'Giáo viên, giáo viên chủ nhiệm'),
    ('COUNSELOR',    'Tham vấn viên',       'Chuyên viên tham vấn tâm lý'),
    ('SCHOOL_ADMIN', 'Quản trị trường',     'Quản lý cấp trường'),
    ('SYSTEM_ADMIN', 'Quản trị hệ thống',  'Quản lý toàn hệ thống')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
    id                  BIGSERIAL PRIMARY KEY,
    school_id           BIGINT REFERENCES schools(id) ON DELETE SET NULL,
    role_id             BIGINT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    full_name           VARCHAR(255) NOT NULL,
    email               VARCHAR(255) UNIQUE,
    phone               VARCHAR(50) UNIQUE,
    username            VARCHAR(100) UNIQUE,
    password_hash       VARCHAR(255),
    avatar_url          VARCHAR(500),
    bio                 TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE, INACTIVE, SUSPENDED
    is_email_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    is_phone_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ  -- soft delete
);

CREATE INDEX IF NOT EXISTS idx_users_school ON users (school_id);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users (role_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status) WHERE deleted_at IS NULL;

-- Profiles
CREATE TABLE IF NOT EXISTS student_profiles (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth   DATE,
    gender          VARCHAR(20),
    class_id        BIGINT,  -- FK added later in education module
    guardian_name   VARCHAR(255),
    guardian_phone  VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    position        VARCHAR(100),
    specialization  VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- MODULE 2: AUTH — tokens
-- =============================================================

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti         VARCHAR(100) NOT NULL UNIQUE,
    user_agent  VARCHAR(500),
    ip_address  VARCHAR(45),
    expires_at  TIMESTAMPTZ NOT NULL,
    is_revoked  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user    ON auth_refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_jti     ON auth_refresh_tokens (jti);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active  ON auth_refresh_tokens (user_id, is_revoked, expires_at);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       VARCHAR(100) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    is_used     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens (token);
CREATE INDEX IF NOT EXISTS idx_password_reset_user  ON password_reset_tokens (user_id);

-- =============================================================
-- MODULE 3: EDUCATION — classes, content, exercises
-- =============================================================

CREATE TABLE IF NOT EXISTS classes (
    id          BIGSERIAL PRIMARY KEY,
    school_id   BIGINT NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    grade       VARCHAR(10),
    teacher_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    academic_year VARCHAR(20),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- FK from student_profiles -> classes (added after classes is created)
ALTER TABLE student_profiles
    ADD CONSTRAINT fk_student_class
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS education_contents (
    id           BIGSERIAL PRIMARY KEY,
    content_type VARCHAR(20) NOT NULL,   -- EXERCISE, BOOKLET, VIDEO, ARTICLE, MINIGAME
    title        VARCHAR(255) NOT NULL,
    description  TEXT,
    topic        VARCHAR(50) NOT NULL,   -- stress, anxiety, bullying, kindness, confidence
    media_url    VARCHAR(500),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_education_contents_type_topic ON education_contents (content_type, topic);

CREATE TABLE IF NOT EXISTS exercise_questions (
    id             BIGSERIAL PRIMARY KEY,
    content_id     BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    question_text  TEXT NOT NULL,
    options        JSONB NOT NULL,
    correct_answer VARCHAR(255) NOT NULL,
    order_index    INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_exercise_questions_content ON exercise_questions (content_id, order_index);

CREATE TABLE IF NOT EXISTS exercise_attempts (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    score            INT,
    duration_seconds INT,
    completed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_exercise_attempts_user ON exercise_attempts (user_id, completed_at DESC);

CREATE TABLE IF NOT EXISTS booklet_reads (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    progress_percent INT NOT NULL DEFAULT 0,
    read_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, content_id)
);

CREATE TABLE IF NOT EXISTS daily_kind_messages (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    category    VARCHAR(50),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- MODULE 4: MOOD DIARY
-- =============================================================

CREATE TABLE IF NOT EXISTS mood_entries (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood_value  INT NOT NULL CHECK (mood_value >= 20 AND mood_value <= 100),
    -- 20=Angry, 40=Sad, 60=Normal, 80=Happy, 100=Great
    note        TEXT,
    mood_date   DATE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, mood_date)
);

CREATE INDEX IF NOT EXISTS idx_mood_entries_user_date ON mood_entries (user_id, mood_date DESC);

-- =============================================================
-- MODULE 5: AI CHATBOT — sessions, messages
-- =============================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
    id                     BIGSERIAL PRIMARY KEY,
    user_id                BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    school_id              BIGINT REFERENCES schools(id) ON DELETE SET NULL,
    status                 VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, ENDED
    started_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at               TIMESTAMPTZ,
    last_risk_level        VARCHAR(20),   -- LOW, MEDIUM, HIGH, CRITICAL
    last_risk_type         VARCHAR(50),   -- EMOTIONAL, BULLYING, SELF_HARM, OTHER
    last_escalation_action VARCHAR(50),
    conversation_summary   TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions (user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_type     VARCHAR(10) NOT NULL,  -- USER, AI
    sender_user_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    content         TEXT NOT NULL,
    risk_level      VARCHAR(20),
    risk_type       VARCHAR(50),
    is_sensitive    BOOLEAN NOT NULL DEFAULT FALSE,
    signals         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages (session_id, created_at);

-- =============================================================
-- MODULE 6: REPORTS — incident reports
-- =============================================================

CREATE TABLE IF NOT EXISTS incident_types (
    id          BIGSERIAL PRIMARY KEY,
    code        VARCHAR(50) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO incident_types (code, name) VALUES
    ('BULLYING',         'Bạo lực học đường'),
    ('SELF_HARM',        'Tự làm hại bản thân'),
    ('MENTAL_HEALTH',    'Vấn đề sức khỏe tâm thần'),
    ('ABUSE',            'Lạm dụng'),
    ('OTHER',            'Khác')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS support_organizations (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    code        VARCHAR(50) UNIQUE,
    description TEXT,
    phone       VARCHAR(50),
    email       VARCHAR(255),
    website     VARCHAR(500),
    address     TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reports (
    id                BIGSERIAL PRIMARY KEY,
    school_id         BIGINT REFERENCES schools(id) ON DELETE SET NULL,
    reporter_user_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_anonymous      BOOLEAN NOT NULL DEFAULT TRUE,
    incident_type_id  BIGINT NOT NULL REFERENCES incident_types(id),
    title             VARCHAR(255),
    content           TEXT NOT NULL,
    location_text     VARCHAR(255),
    location_lat      NUMERIC(10, 7),
    location_lng      NUMERIC(10, 7),
    severity_level    VARCHAR(20) DEFAULT 'LOW',  -- LOW, MEDIUM, HIGH, CRITICAL
    ai_guidance       TEXT,
    status            VARCHAR(30) NOT NULL DEFAULT 'NEW',
    -- NEW, UNDER_REVIEW, IN_PROGRESS, RESOLVED, CLOSED
    submitted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_reports_school_status ON reports (school_id, status) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS report_attachments (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    file_id         BIGINT NOT NULL,
    attachment_type VARCHAR(50) NOT NULL DEFAULT 'OTHER',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_status_history (
    id                  BIGSERIAL PRIMARY KEY,
    report_id           BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    from_status         VARCHAR(30),
    to_status           VARCHAR(30) NOT NULL,
    changed_by_user_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    note                TEXT,
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_ai_analyses (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    model_name      VARCHAR(100) NOT NULL,
    severity_level  VARCHAR(20) NOT NULL,
    risk_type       VARCHAR(50),
    guidance        TEXT,
    raw_result      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- MODULE 7: QUIZ — Candy Crush style quiz system
-- =============================================================

CREATE TABLE IF NOT EXISTS quiz_levels (
    id           BIGSERIAL PRIMARY KEY,
    file_id      VARCHAR(50) NOT NULL UNIQUE,  -- e.g. FILE_1, FILE_2
    set_number   INT NOT NULL,
    set_title    VARCHAR(255) NOT NULL DEFAULT '',
    tags         JSONB NOT NULL DEFAULT '[]',
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    unlock_order INT NOT NULL UNIQUE,  -- Sequential unlock order, no gaps
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_quiz_levels_unlock_order ON quiz_levels (unlock_order);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id                  BIGSERIAL PRIMARY KEY,
    level_id            BIGINT NOT NULL REFERENCES quiz_levels(id) ON DELETE CASCADE,
    question_id         VARCHAR(50) NOT NULL,  -- e.g. F1_Q1
    question_type       VARCHAR(30) NOT NULL,
    -- multiple_choice, fill_blank, matching, ordering
    prompt              TEXT NOT NULL,
    options             JSONB NOT NULL DEFAULT '[]',
    correct_option_id   VARCHAR(10),
    correct_option_text TEXT,
    explanation         TEXT,
    interaction         JSONB NOT NULL DEFAULT '{}',
    -- fill_blank: {sentence_template, sentence_answers, word_bank}
    -- matching:   {left_items, right_items, correct_pairs}
    -- ordering:   {items_to_order, correct_sequence}
    order_index         INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (level_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_level ON quiz_questions (level_id, order_index);

CREATE TABLE IF NOT EXISTS quiz_level_progress (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    level_id         BIGINT NOT NULL REFERENCES quiz_levels(id) ON DELETE CASCADE,
    is_unlocked      BOOLEAN NOT NULL DEFAULT FALSE,
    is_completed     BOOLEAN NOT NULL DEFAULT FALSE,
    best_score       FLOAT NOT NULL DEFAULT 0.0,   -- 0–100%
    stars            SMALLINT NOT NULL DEFAULT 0,   -- 0/1/2/3
    attempts         INT NOT NULL DEFAULT 0,
    last_played_at   TIMESTAMPTZ,
    first_completed_at TIMESTAMPTZ,
    last_attempted_at  TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, level_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_progress_user ON quiz_level_progress (user_id);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    level_id         BIGINT NOT NULL REFERENCES quiz_levels(id) ON DELETE CASCADE,
    score            NUMERIC(5, 2) NOT NULL DEFAULT 0,  -- percentage
    stars            SMALLINT NOT NULL DEFAULT 0,
    total_questions  INT NOT NULL DEFAULT 0,
    correct_answers  INT NOT NULL DEFAULT 0,
    duration_seconds INT,
    answers          JSONB,   -- {question_id: {answer, correct, correct_answer}}
    completed_at     TIMESTAMPTZ DEFAULT now(),
    attempted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_level ON quiz_attempts (user_id, level_id);

-- =============================================================
-- MODULE 8: MISC — files, notifications, system settings
-- =============================================================

CREATE TABLE IF NOT EXISTS files (
    id           BIGSERIAL PRIMARY KEY,
    uploader_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    filename     VARCHAR(255) NOT NULL,
    file_path    VARCHAR(500) NOT NULL,
    file_size    BIGINT,
    mime_type    VARCHAR(100),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    body        TEXT,
    type        VARCHAR(50),
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    data        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications (user_id, is_read, created_at DESC);

CREATE TABLE IF NOT EXISTS system_settings (
    id          BIGSERIAL PRIMARY KEY,
    key         VARCHAR(100) NOT NULL UNIQUE,
    value       TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- SEED: Import quiz data
-- Run this AFTER setup.sql:
--   python import_quiz_from_json.py
-- =============================================================
