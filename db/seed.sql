-- =============================================================
-- CALMI — SEED DATA (Demo/Dev)
-- Chạy SAU setup.sql
-- Password mặc định tất cả: Password123!
-- Hash bcrypt: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.IXbJ9j0xYxNxPu
-- =============================================================

DO $$
DECLARE
    v_school1_id    BIGINT;
    v_school2_id    BIGINT;
    v_role_student  BIGINT;
    v_role_teacher  BIGINT;
    v_role_counselor BIGINT;
    v_role_sadmin   BIGINT;
    v_pass          TEXT := '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.IXbJ9j0xYxNxPu';
    v_class1_id     BIGINT;
    v_class2_id     BIGINT;
    v_student1_id   BIGINT;
    v_student2_id   BIGINT;
    v_student3_id   BIGINT;
    v_teacher1_id   BIGINT;
    v_counselor1_id BIGINT;
BEGIN

-- ============================================================
-- 1. SCHOOLS
-- ============================================================
INSERT INTO schools (code, name, address, province, district, phone, email, status)
VALUES ('HCM001', 'THPT Nguyễn Du', '123 Đinh Tiên Hoàng, P.1', 'Hồ Chí Minh', 'Bình Thạnh', '0281234567', 'contact@nguyendu.edu.vn', 'ACTIVE')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
RETURNING id INTO v_school1_id;

IF v_school1_id IS NULL THEN
    SELECT id INTO v_school1_id FROM schools WHERE code = 'HCM001';
END IF;

INSERT INTO schools (code, name, address, province, district, phone, email, status)
VALUES ('HN001', 'THPT Chu Văn An', '10 Thụy Khuê, Tây Hồ', 'Hà Nội', 'Tây Hồ', '0241234567', 'contact@chuvan.edu.vn', 'ACTIVE')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
RETURNING id INTO v_school2_id;

IF v_school2_id IS NULL THEN
    SELECT id INTO v_school2_id FROM schools WHERE code = 'HN001';
END IF;

-- ============================================================
-- 2. ROLE IDs
-- ============================================================
SELECT id INTO v_role_student   FROM roles WHERE code = 'STUDENT';
SELECT id INTO v_role_teacher   FROM roles WHERE code = 'TEACHER';
SELECT id INTO v_role_counselor FROM roles WHERE code = 'COUNSELOR';
SELECT id INTO v_role_sadmin    FROM roles WHERE code = 'SCHOOL_ADMIN';

-- ============================================================
-- 3. USERS
-- ============================================================

-- Teacher
INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_teacher, 'Trần Thị Lan', 'lan.tran@nguyendu.edu.vn', '0901112233', 'teacher01', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING
RETURNING id INTO v_teacher1_id;

IF v_teacher1_id IS NULL THEN
    SELECT id INTO v_teacher1_id FROM users WHERE username = 'teacher01';
END IF;

INSERT INTO teacher_profiles (user_id, position, specialization)
VALUES (v_teacher1_id, 'Giáo viên chủ nhiệm', 'Văn học')
ON CONFLICT (user_id) DO NOTHING;

-- Counselor
INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_counselor, 'Nguyễn Minh Tuấn', 'tuan.nguyen@nguyendu.edu.vn', '0902223344', 'counselor01', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING
RETURNING id INTO v_counselor1_id;

IF v_counselor1_id IS NULL THEN
    SELECT id INTO v_counselor1_id FROM users WHERE username = 'counselor01';
END IF;

-- School Admin
INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_sadmin, 'Phạm Văn Đức', 'duc.pham@nguyendu.edu.vn', '0903334455', 'admin01', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- 4. CLASSES
-- ============================================================
INSERT INTO classes (school_id, name, grade, homeroom_teacher_id)
VALUES (v_school1_id, '10A1', '10', v_teacher1_id)
ON CONFLICT DO NOTHING
RETURNING id INTO v_class1_id;

IF v_class1_id IS NULL THEN
    SELECT id INTO v_class1_id FROM classes WHERE school_id = v_school1_id AND name = '10A1';
END IF;

INSERT INTO classes (school_id, name, grade, homeroom_teacher_id)
VALUES (v_school1_id, '11B2', '11', v_teacher1_id)
ON CONFLICT DO NOTHING
RETURNING id INTO v_class2_id;

IF v_class2_id IS NULL THEN
    SELECT id INTO v_class2_id FROM classes WHERE school_id = v_school1_id AND name = '11B2';
END IF;

-- ============================================================
-- 5. STUDENTS
-- ============================================================
INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_student, 'Nguyễn Văn An', 'an.nguyen@student.edu.vn', '0911001001', 'student01', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING
RETURNING id INTO v_student1_id;

IF v_student1_id IS NULL THEN
    SELECT id INTO v_student1_id FROM users WHERE username = 'student01';
END IF;

INSERT INTO student_profiles (user_id, date_of_birth, gender, class_id)
VALUES (v_student1_id, '2008-05-15', 'MALE', v_class1_id)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_student, 'Lê Thị Bình', 'binh.le@student.edu.vn', '0911002002', 'student02', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING
RETURNING id INTO v_student2_id;

IF v_student2_id IS NULL THEN
    SELECT id INTO v_student2_id FROM users WHERE username = 'student02';
END IF;

INSERT INTO student_profiles (user_id, date_of_birth, gender, class_id)
VALUES (v_student2_id, '2007-09-20', 'FEMALE', v_class1_id)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO users (school_id, role_id, full_name, email, phone, username, password_hash, status, is_email_verified)
VALUES (v_school1_id, v_role_student, 'Trần Quốc Cường', 'cuong.tran@student.edu.vn', '0911003003', 'student03', v_pass, 'ACTIVE', true)
ON CONFLICT (username) DO NOTHING
RETURNING id INTO v_student3_id;

IF v_student3_id IS NULL THEN
    SELECT id INTO v_student3_id FROM users WHERE username = 'student03';
END IF;

INSERT INTO student_profiles (user_id, date_of_birth, gender, class_id)
VALUES (v_student3_id, '2007-03-10', 'MALE', v_class2_id)
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================
-- 6. MOOD ENTRIES (7 ngày gần nhất cho student01)
-- ============================================================
INSERT INTO mood_entries (user_id, mood_value, note, mood_date) VALUES
    (v_student1_id, 60, 'Ngày bình thường', CURRENT_DATE - 6),
    (v_student1_id, 40, 'Hơi mệt, nhiều bài tập quá', CURRENT_DATE - 5),
    (v_student1_id, 40, 'Buồn vì bị điểm kém môn Toán', CURRENT_DATE - 4),
    (v_student1_id, 60, null, CURRENT_DATE - 3),
    (v_student1_id, 80, 'Vui vì thi tốt!', CURRENT_DATE - 2),
    (v_student1_id, 80, 'Cuối tuần vui vẻ', CURRENT_DATE - 1),
    (v_student1_id, 60, null, CURRENT_DATE)
ON CONFLICT (user_id, mood_date) DO NOTHING;

-- student02
INSERT INTO mood_entries (user_id, mood_value, note, mood_date) VALUES
    (v_student2_id, 100, 'Rất vui!', CURRENT_DATE - 2),
    (v_student2_id, 80, null, CURRENT_DATE - 1),
    (v_student2_id, 80, null, CURRENT_DATE)
ON CONFLICT (user_id, mood_date) DO NOTHING;

-- ============================================================
-- 7. EDUCATION CONTENTS (mẫu)
-- ============================================================
INSERT INTO education_contents (content_type, title, description, topic, is_active) VALUES
    ('ARTICLE', 'Nhận diện căng thẳng học đường', 'Hướng dẫn nhận biết các dấu hiệu stress sớm', 'stress', true),
    ('ARTICLE', 'Kỹ năng quản lý cảm xúc', 'Các bài tập 5 phút giúp bình tâm nhanh chóng', 'anxiety', true),
    ('ARTICLE', 'Hiểu về bạo lực học đường', 'Phân loại và cách ứng phó', 'bullying', true)
ON CONFLICT DO NOTHING;

-- ============================================================
-- 8. SYSTEM SETTINGS
-- ============================================================
INSERT INTO system_settings (key, value, description) VALUES
    ('app_version',        '1.0.0',   'Phiên bản ứng dụng'),
    ('maintenance_mode',   'false',   'Chế độ bảo trì'),
    ('quiz_pass_threshold','50',      '% tối thiểu để đạt 1 sao')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

RAISE NOTICE '✅ Seed hoàn tất!';
RAISE NOTICE '';
RAISE NOTICE '=== TÀI KHOẢN TEST (password: Password123!) ===';
RAISE NOTICE 'student01    → Học sinh';
RAISE NOTICE 'student02    → Học sinh';
RAISE NOTICE 'student03    → Học sinh';
RAISE NOTICE 'teacher01    → Giáo viên';
RAISE NOTICE 'counselor01  → Tham vấn viên';
RAISE NOTICE 'admin01      → Quản trị trường';

END $$;
