-- Namunaviy ma'lumotlar (schema.sql dan keyin bajariladi)
-- Parollar pgcrypto bilan bcrypt formatida shifrlanadi (Python bcrypt bilan mos).
-- Kirish: admin / Admin123!   teacher1 / Teacher123!   teacher2 / Teacher123!
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO users (username, email, password_hash, full_name, role) VALUES
 ('admin',    'nabdurazaqov@gmail.com', crypt('Admin123!',   gen_salt('bf', 12)), 'Tizim administratori', 'ADMIN'),
 ('teacher1', 'karimov@univ.uz',        crypt('Teacher123!', gen_salt('bf', 12)), 'Karimov Anvar',        'TEACHER'),
 ('teacher2', 'saidova@univ.uz',        crypt('Teacher123!', gen_salt('bf', 12)), 'Saidova Dilnoza',      'TEACHER');

INSERT INTO teachers (user_id, department, phone)
SELECT id, 'Axborot texnologiyalari', '+998901112233' FROM users WHERE username = 'teacher1';
INSERT INTO teachers (user_id, department, phone)
SELECT id, 'Matematika', '+998909998877' FROM users WHERE username = 'teacher2';

INSERT INTO groups (name, course_year, specialty, curator_id)
SELECT 'DI-21-01', 3, 'Dasturiy injiniring', t.id FROM teachers t JOIN users u ON u.id = t.user_id WHERE u.username = 'teacher1';
INSERT INTO groups (name, course_year, specialty, curator_id)
SELECT 'DI-21-02', 3, 'Dasturiy injiniring', t.id FROM teachers t JOIN users u ON u.id = t.user_id WHERE u.username = 'teacher2';

INSERT INTO subjects (code, name, credits, semester, teacher_id)
SELECT 'CS101', 'Ma''lumotlar bazasi', 4, 5, t.id FROM teachers t JOIN users u ON u.id = t.user_id WHERE u.username = 'teacher1';
INSERT INTO subjects (code, name, credits, semester, teacher_id)
SELECT 'CS102', 'Dasturlash asoslari', 4, 5, t.id FROM teachers t JOIN users u ON u.id = t.user_id WHERE u.username = 'teacher2';
INSERT INTO subjects (code, name, credits, semester, teacher_id)
SELECT 'MA101', 'Diskret matematika', 3, 5, t.id FROM teachers t JOIN users u ON u.id = t.user_id WHERE u.username = 'teacher2';

INSERT INTO students (student_code, full_name, email, group_id)
SELECT v.code, v.name, v.email, g.id
FROM (VALUES
  ('S001','Aliyev Jasur',     'jasur@mail.uz',  'DI-21-01'),
  ('S002','Berdiyeva Madina', 'madina@mail.uz', 'DI-21-01'),
  ('S003','Ismoilov Sardor',  'sardor@mail.uz', 'DI-21-01'),
  ('S004','Rahimova Nigora',  'nigora@mail.uz', 'DI-21-01'),
  ('S005','Tursunov Bekzod',  'bekzod@mail.uz', 'DI-21-02'),
  ('S006','Yusupova Zilola',  'zilola@mail.uz', 'DI-21-02'),
  ('S007','Qodirov Otabek',   'otabek@mail.uz', 'DI-21-02'),
  ('S008','Nazarova Malika',  'malika@mail.uz', 'DI-21-02')
) AS v(code, name, email, grp)
JOIN groups g ON g.name = v.grp;

-- Har bir talaba uch fanga ham yoziladi (M:N)
INSERT INTO enrollments (student_id, subject_id)
SELECT s.id, sb.id FROM students s CROSS JOIN subjects sb;

-- Baholar: S001,S002 - yaxshi; S003 - o'rtacha; S004 - pasayayotgan; S005 - past; S006..S008 - turlicha
INSERT INTO grades (enrollment_id, grade_type, score, max_score, graded_at)
SELECT e.id, v.gtype, v.score, 100, CURRENT_DATE - v.days
FROM (VALUES
  ('S001','CS101','CURRENT',88,40),('S001','CS101','MIDTERM',91,20),('S001','CS102','CURRENT',85,35),
  ('S002','CS101','CURRENT',92,40),('S002','CS102','CURRENT',89,30),('S002','MA101','MIDTERM',94,18),
  ('S003','CS101','CURRENT',65,40),('S003','CS102','CURRENT',58,30),('S003','MA101','MIDTERM',61,18),
  ('S004','CS101','CURRENT',90,40),('S004','CS101','CURRENT',84,30),('S004','CS102','CURRENT',70,20),('S004','MA101','MIDTERM',48,10),
  ('S005','CS101','CURRENT',32,40),('S005','CS102','CURRENT',41,30),('S005','MA101','MIDTERM',28,18),
  ('S006','CS101','CURRENT',77,40),('S006','CS102','MIDTERM',72,20),
  ('S007','CS101','CURRENT',45,35),('S007','MA101','CURRENT',52,25),
  ('S008','CS102','CURRENT',95,30),('S008','MA101','MIDTERM',97,15)
) AS v(code, subj, gtype, score, days)
JOIN students s   ON s.student_code = v.code
JOIN subjects sb  ON sb.code = v.subj
JOIN enrollments e ON e.student_id = s.id AND e.subject_id = sb.id;

-- Davomat: har talaba uchun CS101 fanidan 5 ta dars
INSERT INTO attendance (enrollment_id, lesson_date, status)
SELECT e.id, CURRENT_DATE - (d.n * 7), CASE
    WHEN s.student_code IN ('S001','S002','S008')           THEN 'PRESENT'
    WHEN s.student_code IN ('S003','S006') AND d.n IN (2,4) THEN 'ABSENT'
    WHEN s.student_code = 'S003'                            THEN 'PRESENT'
    WHEN s.student_code = 'S004' AND d.n <= 2               THEN 'ABSENT'
    WHEN s.student_code = 'S004'                            THEN 'PRESENT'
    WHEN s.student_code = 'S006'                            THEN 'LATE'
    WHEN s.student_code IN ('S005','S007') AND d.n = 5      THEN 'LATE'
    ELSE 'ABSENT'
  END
FROM students s
JOIN subjects sb ON sb.code = 'CS101'
JOIN enrollments e ON e.student_id = s.id AND e.subject_id = sb.id
CROSS JOIN (VALUES (1),(2),(3),(4),(5)) AS d(n);

-- Risk baholash (trend = 0 deb olingan soddalashtirilgan SQL variant).
-- Formula: 0.5*(100-ball) + 0.3*(100-davomat) + 0.2*trend.
-- Ilovadagi to'liq algoritm trendni ham hisoblaydi:  POST /api/risk/recalculate
WITH g AS (
  SELECT e.student_id,
         SUM(gr.score / gr.max_score * 100 * w.weight) / SUM(w.weight) AS avg_score
  FROM grades gr
  JOIN enrollments e ON e.id = gr.enrollment_id
  JOIN (VALUES ('CURRENT', 1.0), ('MIDTERM', 1.5), ('FINAL', 2.0)) AS w(grade_type, weight)
       ON w.grade_type = gr.grade_type
  GROUP BY e.student_id
), a AS (
  SELECT e.student_id,
         SUM(CASE at.status WHEN 'PRESENT' THEN 1.0 WHEN 'LATE' THEN 0.5 ELSE 0 END) * 100.0
           / NULLIF(COUNT(*) FILTER (WHERE at.status <> 'EXCUSED'), 0) AS att_rate
  FROM attendance at
  JOIN enrollments e ON e.id = at.enrollment_id
  GROUP BY e.student_id
), r AS (
  SELECT g.student_id, g.avg_score, a.att_rate,
         0.5 * (100 - g.avg_score) + 0.3 * (100 - a.att_rate) AS score
  FROM g JOIN a ON a.student_id = g.student_id
)
INSERT INTO risk_assessments (student_id, avg_score, attendance_rate, trend_score, risk_score, risk_level)
SELECT student_id, ROUND(avg_score::numeric, 2), ROUND(att_rate::numeric, 2), 0,
       ROUND(score::numeric, 2),
       CASE WHEN score >= 70 THEN 'CRITICAL' WHEN score >= 50 THEN 'HIGH'
            WHEN score >= 30 THEN 'MEDIUM' ELSE 'LOW' END
FROM r;

COMMIT;
