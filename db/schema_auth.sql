-- schema_auth.sql
-- PostgreSQL migration cho Auth module
-- Tao cac bang luu tru refresh tokens va password reset tokens

-- ==========================================
-- 1. AUTH REFRESH TOKENS
-- ==========================================
-- Luu tru refresh tokens cho tinh nang revoke va token rotation

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti             VARCHAR(100) NOT NULL UNIQUE,  -- JWT ID, dung de identify token
    user_agent      VARCHAR(500),                   -- Thong tin trinh duyet/thiet bi
    ip_address      VARCHAR(45),                    -- IPv4 hoac IPv6
    expires_at      TIMESTAMPTZ NOT NULL,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

-- Index de tim token theo user (logout all devices)
CREATE INDEX idx_refresh_tokens_user_id ON auth_refresh_tokens (user_id);

-- Index de tim token theo jti (validation)
CREATE INDEX idx_refresh_tokens_jti ON auth_refresh_tokens (jti);

-- Index de tim active tokens (chua revoke, chua het han)
CREATE INDEX idx_refresh_tokens_active ON auth_refresh_tokens (user_id, is_revoked, expires_at);


-- ==========================================
-- 2. PASSWORD RESET TOKENS
-- ==========================================
-- Luu tru tokens cho tinh nang forgot password

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(100) NOT NULL UNIQUE,   -- Token gui qua email
    expires_at      TIMESTAMPTZ NOT NULL,
    is_used         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ
);

-- Index de tim token (validation)
CREATE INDEX idx_password_reset_token ON password_reset_tokens (token);

-- Index de tim tokens cua user
CREATE INDEX idx_password_reset_user ON password_reset_tokens (user_id);
