-- schema_reports.sql
-- PostgreSQL migration for Module 1 - Anonymous Reporting
-- Tables: incident_types, reports, report_ai_analyses, report_destinations,
--         report_attachments, report_status_history

-- ==========================================
-- 1. INCIDENT TYPES
-- ==========================================
-- Lookup table for types of incidents

CREATE TABLE IF NOT EXISTS incident_types (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed initial incident types
INSERT INTO incident_types (code, name, description) VALUES
    ('PHYSICAL', 'Bao luc the chat', 'Danh dap, xo day, gay thuong tich'),
    ('VERBAL', 'Bao luc loi noi', 'Chui boi, mang nhiec, de doa'),
    ('CYBERBULLYING', 'Bao luc mang', 'Quay roi qua mang xa hoi, tin nhan'),
    ('SEXUAL', 'Quay roi tinh duc', 'Hanh vi xam hai tinh duc'),
    ('EXCLUSION', 'Co lap xa hoi', 'Tay chay, loai tru khoi nhom'),
    ('PROPERTY', 'Pha hoai tai san', 'Hu hong, an cap do dung'),
    ('SELF_HARM', 'Tu gay thuong', 'Hoc sinh co y dinh tu gay thuong'),
    ('OTHER', 'Khac', 'Cac truong hop khac')
ON CONFLICT (code) DO NOTHING;


-- ==========================================
-- 2. REPORTS
-- ==========================================
-- Main reports table storing anonymous submissions

CREATE TABLE IF NOT EXISTS reports (
    id                  BIGSERIAL PRIMARY KEY,
    school_id           BIGINT REFERENCES schools(id) ON DELETE SET NULL,
    reporter_user_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_anonymous        BOOLEAN NOT NULL DEFAULT TRUE,
    incident_type_id    BIGINT NOT NULL REFERENCES incident_types(id),
    title               VARCHAR(255),
    content             TEXT NOT NULL,
    location_text       VARCHAR(500),
    location_lat        DECIMAL(10, 8),
    location_lng        DECIMAL(11, 8),
    severity_level      VARCHAR(20) DEFAULT 'LOW',  -- LOW, MEDIUM, HIGH, EMERGENCY
    ai_guidance         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'NEW',  -- NEW, IN_PROGRESS, RESOLVED, CLOSED
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

-- Indexes for reports
CREATE INDEX idx_reports_school_submitted ON reports (school_id, submitted_at);
CREATE INDEX idx_reports_reporter ON reports (reporter_user_id);
CREATE INDEX idx_reports_severity ON reports (severity_level);
CREATE INDEX idx_reports_status ON reports (status);
CREATE INDEX idx_reports_incident_type ON reports (incident_type_id);


-- ==========================================
-- 3. REPORT AI ANALYSES
-- ==========================================
-- Full log of AI analysis results for audit trail

CREATE TABLE IF NOT EXISTS report_ai_analyses (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    model_name      VARCHAR(100) NOT NULL,
    severity_level  VARCHAR(20) NOT NULL,
    risk_type       VARCHAR(50),  -- BULLYING, SELF_HARM, OTHER
    guidance        TEXT,
    raw_result      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for AI analyses
CREATE INDEX idx_report_ai_report_created ON report_ai_analyses (report_id, created_at);


-- ==========================================
-- 4. REPORT DESTINATIONS
-- ==========================================
-- Where the report is sent to

CREATE TABLE IF NOT EXISTS report_destinations (
    id                          BIGSERIAL PRIMARY KEY,
    report_id                   BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    destination_type            VARCHAR(30) NOT NULL,  -- INTERNAL_USER, SUPPORT_ORG, EMAIL
    destination_user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    destination_support_org_id  BIGINT REFERENCES support_organizations(id) ON DELETE SET NULL,
    destination_email           VARCHAR(255),
    delivery_channel            VARCHAR(20) NOT NULL,  -- IN_APP, EMAIL
    status                      VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, SENT, FAILED
    last_error                  TEXT,
    sent_at                     TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for destinations
CREATE INDEX idx_report_dest_report ON report_destinations (report_id);
CREATE INDEX idx_report_dest_type_status ON report_destinations (destination_type, status);
CREATE INDEX idx_report_dest_user ON report_destinations (destination_user_id);


-- ==========================================
-- 5. REPORT ATTACHMENTS
-- ==========================================
-- Links reports to anonymized files

CREATE TABLE IF NOT EXISTS report_attachments (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    file_id         BIGINT NOT NULL REFERENCES files(id) ON DELETE RESTRICT,
    attachment_type VARCHAR(20) NOT NULL DEFAULT 'OTHER',  -- IMAGE, VIDEO, AUDIO, DOCUMENT, OTHER
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for attachments
CREATE INDEX idx_report_attach_report ON report_attachments (report_id);


-- ==========================================
-- 6. REPORT STATUS HISTORY
-- ==========================================
-- Audit trail of status changes

CREATE TABLE IF NOT EXISTS report_status_history (
    id                  BIGSERIAL PRIMARY KEY,
    report_id           BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    from_status         VARCHAR(20),
    to_status           VARCHAR(20) NOT NULL,
    changed_by_user_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    note                TEXT,
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for status history
CREATE INDEX idx_report_status_hist ON report_status_history (report_id, changed_at);
