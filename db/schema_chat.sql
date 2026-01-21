-- ==========================================
-- MODULE 3: AI PSYCHOLOGICAL CHATBOT
-- Tables: chat_sessions, chat_messages
-- ==========================================

-- ==========================================
-- 1. CHAT SESSIONS
-- ==========================================
CREATE TABLE chat_sessions (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    school_id        BIGINT REFERENCES schools(id) ON DELETE SET NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, ENDED
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at         TIMESTAMPTZ NULL,
    last_risk_level  VARCHAR(20) NULL,      -- LOW, MEDIUM, HIGH, CRITICAL
    last_risk_type   VARCHAR(50) NULL,      -- EMOTIONAL, BULLYING, SELF_HARM, OTHER
    last_escalation_action VARCHAR(50) NULL,
    conversation_summary TEXT NULL,   -- LangChain conversation summary
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for chat_sessions
CREATE INDEX idx_chat_sessions_user_started ON chat_sessions (user_id, started_at DESC);
CREATE INDEX idx_chat_sessions_status ON chat_sessions (status);

-- ==========================================
-- 2. CHAT MESSAGES
-- ==========================================
CREATE TABLE chat_messages (
    id               BIGSERIAL PRIMARY KEY,
    session_id       BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_type      VARCHAR(20) NOT NULL,  -- USER, AI
    sender_user_id   BIGINT REFERENCES users(id) ON DELETE SET NULL,  -- Only for USER type
    content          TEXT NOT NULL,
    risk_level       VARCHAR(20) NULL,      -- LOW, MEDIUM, HIGH, CRITICAL
    risk_type        VARCHAR(50) NULL,      -- EMOTIONAL, BULLYING, SELF_HARM, OTHER
    is_sensitive     BOOLEAN NOT NULL DEFAULT FALSE,
    signals          JSONB NULL,            -- Matched patterns/keywords for audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for chat_messages
CREATE INDEX idx_chat_messages_session_created ON chat_messages (session_id, created_at);
CREATE INDEX idx_chat_messages_risk_level ON chat_messages (risk_level);

-- ==========================================
-- COMMENTS
-- ==========================================
COMMENT ON TABLE chat_sessions IS 'Student chat sessions with AI psychological chatbot';
COMMENT ON COLUMN chat_sessions.last_risk_level IS 'Cached risk level from latest message for quick access';
COMMENT ON COLUMN chat_sessions.last_escalation_action IS 'Last recommended escalation action';

COMMENT ON TABLE chat_messages IS 'Individual messages in chat sessions';
COMMENT ON COLUMN chat_messages.sender_type IS 'USER for student messages, AI for chatbot responses';
COMMENT ON COLUMN chat_messages.signals IS 'JSON array of matched risk keywords/patterns for audit';
COMMENT ON COLUMN chat_messages.is_sensitive IS 'Flag for messages containing sensitive content';
