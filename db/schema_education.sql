-- ==========================================
-- MODULE 4: PREVENTIVE EDUCATION & POSITIVE MENTAL HEALTH
-- Tables: education_contents, exercise_questions, exercise_attempts,
--         booklet_reads, minigame_results, daily_kind_messages, daily_kind_responses
-- ==========================================

-- ==========================================
-- 1. EDUCATION CONTENTS
-- Stores all educational content types
-- ==========================================
CREATE TABLE education_contents (
    id               BIGSERIAL PRIMARY KEY,
    content_type     VARCHAR(20) NOT NULL,  -- EXERCISE, BOOKLET, VIDEO, ARTICLE, MINIGAME
    title            VARCHAR(255) NOT NULL,
    description      TEXT NULL,
    topic            VARCHAR(50) NOT NULL,  -- stress, anxiety, bullying, kindness, confidence
    media_url        VARCHAR(500) NULL,     -- video/pdf/url
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_education_contents_type_topic ON education_contents (content_type, topic);
CREATE INDEX idx_education_contents_active ON education_contents (is_active);

-- ==========================================
-- 2. EXERCISE QUESTIONS (for QUIZ type)
-- ==========================================
CREATE TABLE exercise_questions (
    id               BIGSERIAL PRIMARY KEY,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    question_text    TEXT NOT NULL,
    options          JSONB NOT NULL,         -- ["Option A", "Option B", "Option C", "Option D"]
    correct_answer   VARCHAR(255) NOT NULL,  -- The correct option
    order_index      INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_exercise_questions_content ON exercise_questions (content_id, order_index);

-- ==========================================
-- 3. EXERCISE ATTEMPTS
-- Student exercise completion history
-- ==========================================
CREATE TABLE exercise_attempts (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    score            INT NULL,               -- For quizzes: percentage or points
    duration_seconds INT NULL,               -- How long it took
    completed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_exercise_attempts_user_date ON exercise_attempts (user_id, completed_at DESC);
CREATE INDEX idx_exercise_attempts_content ON exercise_attempts (content_id);

-- ==========================================
-- 4. BOOKLET READS
-- Track student reading progress
-- ==========================================
CREATE TABLE booklet_reads (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    progress_percent INT NOT NULL DEFAULT 0,  -- 0-100
    read_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_booklet_reads_user ON booklet_reads (user_id, read_at DESC);
CREATE UNIQUE INDEX idx_booklet_reads_user_content ON booklet_reads (user_id, content_id);

-- ==========================================
-- 5. MINIGAME RESULTS
-- Store game play results and rewards
-- ==========================================
CREATE TABLE minigame_results (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id       BIGINT NOT NULL REFERENCES education_contents(id) ON DELETE CASCADE,
    score            INT NOT NULL DEFAULT 0,
    reward_points    INT NOT NULL DEFAULT 0,
    played_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_minigame_results_user ON minigame_results (user_id, played_at DESC);
CREATE INDEX idx_minigame_results_content ON minigame_results (content_id);

-- ==========================================
-- 6. DAILY KIND MESSAGES
-- Positive messages sent each day
-- ==========================================
CREATE TABLE daily_kind_messages (
    id               BIGSERIAL PRIMARY KEY,
    message_text     TEXT NOT NULL,
    active_date      DATE NOT NULL,          -- The date this message is active
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_daily_kind_messages_date ON daily_kind_messages (active_date);

-- ==========================================
-- 7. DAILY KIND RESPONSES
-- Student responses to daily messages
-- ==========================================
CREATE TABLE daily_kind_responses (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id       BIGINT NOT NULL REFERENCES daily_kind_messages(id) ON DELETE CASCADE,
    response_text    TEXT NOT NULL,
    responded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_daily_kind_responses_user ON daily_kind_responses (user_id, responded_at DESC);
CREATE UNIQUE INDEX idx_daily_kind_responses_user_message ON daily_kind_responses (user_id, message_id);

-- ==========================================
-- COMMENTS
-- ==========================================
COMMENT ON TABLE education_contents IS 'All educational content: exercises, booklets, videos, articles, minigames';
COMMENT ON COLUMN education_contents.content_type IS 'EXERCISE, BOOKLET, VIDEO, ARTICLE, MINIGAME';
COMMENT ON COLUMN education_contents.topic IS 'stress, anxiety, bullying, kindness, confidence, emotional_regulation';

COMMENT ON TABLE exercise_questions IS 'Quiz questions for EXERCISE type content';
COMMENT ON COLUMN exercise_questions.options IS 'JSON array of answer options';

COMMENT ON TABLE exercise_attempts IS 'Student completion records for exercises';
COMMENT ON TABLE booklet_reads IS 'Student reading progress for booklets';
COMMENT ON TABLE minigame_results IS 'Minigame play results with gamification points';
COMMENT ON TABLE daily_kind_messages IS 'Daily positive messages';
COMMENT ON TABLE daily_kind_responses IS 'Student responses to daily kind messages';

-- ==========================================
-- SEED DATA: Sample daily messages
-- ==========================================
INSERT INTO daily_kind_messages (message_text, active_date) VALUES
('Hôm nay, hãy thử nói một điều tốt đẹp với ai đó nhé! 💚', CURRENT_DATE),
('Mỉm cười với một người bạn mới hôm nay. Bạn có thể làm được! 😊', CURRENT_DATE + 1),
('Hãy cảm ơn một người đã giúp đỡ bạn gần đây. 🙏', CURRENT_DATE + 2);

-- ==========================================
-- SEED DATA: Sample educational content
-- ==========================================
INSERT INTO education_contents (content_type, title, description, topic, is_active) VALUES
('EXERCISE', 'Bài tập hít thở 4-7-8', 'Kỹ thuật hít thở giúp giảm căng thẳng và lo âu', 'stress', TRUE),
('EXERCISE', 'Nhận diện cảm xúc', 'Quiz giúp bạn hiểu rõ cảm xúc của mình', 'emotional_regulation', TRUE),
('BOOKLET', 'Nhận biết bắt nạt học đường', 'Tài liệu về các dấu hiệu bắt nạt và cách ứng phó', 'bullying', TRUE),
('BOOKLET', 'Quyền trẻ em', 'Những điều bạn cần biết về quyền của mình', 'kindness', TRUE),
('VIDEO', 'Thiền chánh niệm 5 phút', 'Video hướng dẫn thiền đơn giản cho học sinh', 'anxiety', TRUE),
('MINIGAME', 'Bạn sẽ làm gì?', 'Game tình huống về ứng xử khi chứng kiến bắt nạt', 'bullying', TRUE),
('ARTICLE', 'Câu chuyện về lòng tốt', 'Những câu chuyện truyền cảm hứng về sự tử tế', 'kindness', TRUE);
