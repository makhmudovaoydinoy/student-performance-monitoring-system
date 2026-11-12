-- ============ Asosiy SELECT so'rovlari ============

-- 1. Talabalar ro'yxati guruh nomi bilan
SELECT s.student_code, s.full_name, g.name AS guruh, s.status
FROM students s JOIN groups g ON g.id = s.group_id
ORDER BY g.name, s.full_name;

-- 2. Har bir talabaning oxirgi risk bahosi (view orqali)
SELECT s.student_code, s.full_name, r.avg_score, r.attendance_rate, r.risk_score, r.risk_level
FROM students s LEFT JOIN v_latest_risk r ON r.student_id = s.id
ORDER BY r.risk_score DESC NULLS LAST;

-- 3. Xavf guruhi: HIGH va CRITICAL talabalar
SELECT s.student_code, s.full_name, g.name AS guruh, r.risk_score, r.risk_level
FROM v_latest_risk r
JOIN students s ON s.id = r.student_id
JOIN groups g   ON g.id = s.group_id
WHERE r.risk_level IN ('HIGH', 'CRITICAL')
ORDER BY r.risk_score DESC;

-- 4. Talabaning fanlar kesimidagi o'rtacha bahosi (foizda)
SELECT sb.name AS fan, ROUND(AVG(gr.score / gr.max_score * 100), 2) AS ortacha_foiz, COUNT(*) AS baholar_soni
FROM grades gr
JOIN enrollments e ON e.id = gr.enrollment_id
JOIN subjects sb   ON sb.id = e.subject_id
WHERE e.student_id = 1
GROUP BY sb.name;

-- 5. Davomat foizi: har bir talaba bo'yicha
SELECT s.full_name,
       ROUND(100.0 * SUM(CASE at.status WHEN 'PRESENT' THEN 1 WHEN 'LATE' THEN 0.5 ELSE 0 END)
             / NULLIF(COUNT(*) FILTER (WHERE at.status <> 'EXCUSED'), 0), 2) AS davomat_foizi
FROM attendance at
JOIN enrollments e ON e.id = at.enrollment_id
JOIN students s    ON s.id = e.student_id
GROUP BY s.full_name
ORDER BY davomat_foizi;

-- 6. Guruhlar kesimida risk taqsimoti
SELECT g.name AS guruh, r.risk_level, COUNT(*) AS talabalar_soni
FROM groups g
JOIN students s ON s.group_id = g.id
JOIN v_latest_risk r ON r.student_id = s.id
GROUP BY g.name, r.risk_level
ORDER BY g.name, r.risk_level;

-- 7. O'qituvchi o'z fanlaridagi talabalar (teacher_id = 1)
SELECT DISTINCT s.student_code, s.full_name
FROM subjects sb
JOIN enrollments e ON e.subject_id = sb.id
JOIN students s    ON s.id = e.student_id
WHERE sb.teacher_id = 1
ORDER BY s.full_name;

-- 8. O'qilmagan xabarnomalar (foydalanuvchi id = 2)
SELECT n.id, n.title, n.created_at
FROM notifications n
WHERE n.recipient_user_id = 2 AND n.is_read = FALSE
ORDER BY n.created_at DESC;

-- 9. Keyingi 30 kunda eng ko'p qoldirilgan darslar (davomat xavfi)
SELECT s.full_name, COUNT(*) AS qoldirilgan
FROM attendance at
JOIN enrollments e ON e.id = at.enrollment_id
JOIN students s    ON s.id = e.student_id
WHERE at.status = 'ABSENT' AND at.lesson_date >= CURRENT_DATE - 30
GROUP BY s.full_name
HAVING COUNT(*) >= 2
ORDER BY qoldirilgan DESC;
