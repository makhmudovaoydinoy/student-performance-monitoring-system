-- ============================================================
-- Talabalar o'zlashtirishini kuzatish va erta ogohlantirish tizimi
-- PostgreSQL 14+ | 10 ta asosiy jadval + 1 ta view
-- ============================================================
BEGIN;

-- 1. users: tizimga kiruvchi foydalanuvchilar (ADMIN / TEACHER)
CREATE TABLE users (
    id            SERIAL       PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    role          VARCHAR(10)  NOT NULL CHECK (role IN ('ADMIN', 'TEACHER')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 2. teachers: o'qituvchi profili (users bilan 1:1)
CREATE TABLE teachers (
    id         SERIAL       PRIMARY KEY,
    user_id    INTEGER      NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department VARCHAR(100),
    phone      VARCHAR(20)
);

-- 3. groups: akademik guruhlar (kurator - o'qituvchi)
CREATE TABLE groups (
    id          SERIAL      PRIMARY KEY,
    name        VARCHAR(30) NOT NULL UNIQUE,
    course_year SMALLINT    NOT NULL CHECK (course_year BETWEEN 1 AND 6),
    specialty   VARCHAR(100) NOT NULL,
    curator_id  INTEGER     REFERENCES teachers(id) ON DELETE SET NULL,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- 4. students
CREATE TABLE students (
    id           SERIAL       PRIMARY KEY,
    student_code VARCHAR(20)  NOT NULL UNIQUE,
    full_name    VARCHAR(120) NOT NULL,
    email        VARCHAR(120),
    phone        VARCHAR(20),
    birth_date   DATE,
    group_id     INTEGER      NOT NULL REFERENCES groups(id) ON DELETE RESTRICT,
    status       VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'LEAVE', 'EXPELLED')),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);


-- 4a. student_accounts: talaba uchun alohida login-parol
CREATE TABLE student_accounts (
    id            SERIAL       PRIMARY KEY,
    student_id    INTEGER      NOT NULL UNIQUE REFERENCES students(id) ON DELETE CASCADE,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 5. subjects (fan -> bitta mas'ul o'qituvchi)
CREATE TABLE subjects (
    id         SERIAL       PRIMARY KEY,
    code       VARCHAR(20)  NOT NULL UNIQUE,
    name       VARCHAR(120) NOT NULL,
    credits    SMALLINT     NOT NULL DEFAULT 3 CHECK (credits > 0),
    semester   SMALLINT     NOT NULL DEFAULT 1 CHECK (semester BETWEEN 1 AND 12),
    teacher_id INTEGER      REFERENCES teachers(id) ON DELETE SET NULL
);

-- 6. enrollments: talaba <-> fan (M:N bog'lovchi jadval)
CREATE TABLE enrollments (
    id          SERIAL  PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    enrolled_at DATE    NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT uq_enrollment UNIQUE (student_id, subject_id)
);

-- 7. grades
CREATE TABLE grades (
    id            SERIAL       PRIMARY KEY,
    enrollment_id INTEGER      NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    grade_type    VARCHAR(10)  NOT NULL DEFAULT 'CURRENT' CHECK (grade_type IN ('CURRENT', 'MIDTERM', 'FINAL')),
    score         NUMERIC(5,2) NOT NULL CHECK (score >= 0),
    max_score     NUMERIC(5,2) NOT NULL DEFAULT 100 CHECK (max_score > 0),
    graded_at     DATE         NOT NULL DEFAULT CURRENT_DATE,
    comment       VARCHAR(255),
    created_by    INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_grade_range CHECK (score <= max_score)
);

-- 8. attendance
CREATE TABLE attendance (
    id            SERIAL      PRIMARY KEY,
    enrollment_id INTEGER     NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    lesson_date   DATE        NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'PRESENT' CHECK (status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')),
    note          VARCHAR(255),
    created_by    INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_attendance UNIQUE (enrollment_id, lesson_date)
);

-- 9. risk_assessments: har bir hisoblash natijasi (tarix saqlanadi)
CREATE TABLE risk_assessments (
    id              SERIAL       PRIMARY KEY,
    student_id      INTEGER      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    avg_score       NUMERIC(5,2),
    attendance_rate NUMERIC(5,2),
    trend_score     NUMERIC(5,2) NOT NULL DEFAULT 0,
    risk_score      NUMERIC(5,2) NOT NULL,
    risk_level      VARCHAR(10)  NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    calculated_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 10. notifications
CREATE TABLE notifications (
    id                 SERIAL       PRIMARY KEY,
    recipient_user_id  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id         INTEGER      REFERENCES students(id) ON DELETE CASCADE,
    risk_assessment_id INTEGER      REFERENCES risk_assessments(id) ON DELETE SET NULL,
    title              VARCHAR(150) NOT NULL,
    message            TEXT         NOT NULL,
    channel            VARCHAR(10)  NOT NULL DEFAULT 'IN_APP' CHECK (channel IN ('IN_APP', 'EMAIL')),
    status             VARCHAR(10)  NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    is_read            BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
    sent_at            TIMESTAMP
);

-- ---------------- INDEXLAR ----------------
CREATE INDEX idx_students_group        ON students(group_id);
CREATE INDEX idx_students_full_name    ON students(full_name);
CREATE INDEX idx_subjects_teacher      ON subjects(teacher_id);
CREATE INDEX idx_groups_curator        ON groups(curator_id);
CREATE INDEX idx_enrollments_subject   ON enrollments(subject_id);
CREATE INDEX idx_grades_enrollment     ON grades(enrollment_id, graded_at);
CREATE INDEX idx_attendance_enrollment ON attendance(enrollment_id, lesson_date);
CREATE INDEX idx_risk_student_time     ON risk_assessments(student_id, calculated_at DESC);
CREATE INDEX idx_risk_level            ON risk_assessments(risk_level);
CREATE INDEX idx_notif_recipient       ON notifications(recipient_user_id, is_read);

-- ---------------- VIEW: har bir talabaning oxirgi risk bahosi ----------------
CREATE VIEW v_latest_risk AS
SELECT DISTINCT ON (student_id) *
FROM risk_assessments
ORDER BY student_id, calculated_at DESC, id DESC;

COMMIT;
