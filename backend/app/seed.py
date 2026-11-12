"""Demo ma'lumotlar: python -m app.seed  (backend papkasidan). Qayta ishga tushirsa, mavjud bo'lsa o'tkazib yuboradi."""
import random
from datetime import date, timedelta

from sqlalchemy import func, select

from .database import Base, SessionLocal, engine
from .models import Attendance, Enrollment, Grade, Group, Student, Subject, Teacher, User
from .security import hash_password
from .services.risk_service import assess_all

FIRST = ["Jasur", "Madina", "Sardor", "Nigora", "Bekzod", "Zilola", "Otabek", "Malika", "Aziz", "Dilshod",
         "Sevara", "Rustam", "Gulnora", "Javlon", "Kamola", "Timur", "Nodira", "Sherzod", "Feruza", "Doniyor"]
LAST = ["Aliyev", "Berdiyeva", "Ismoilov", "Rahimova", "Tursunov", "Yusupova", "Qodirov", "Nazarova"]

# profil: (boshlang'ich ball, oxirgi ball, davomat ehtimoli)
PROFILES = [(88, 90, 0.97), (80, 82, 0.92), (68, 66, 0.85), (85, 45, 0.70), (45, 40, 0.65), (35, 30, 0.55)]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    rnd = random.Random(42)
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))) and db.scalar(select(func.count(Student.id))):
            print("Ma'lumotlar allaqachon mavjud, seed o'tkazib yuborildi.")
            return
        if not db.scalar(select(User).where(User.username == "admin")):
            db.add(User(username="admin", email="nabdurazaqov@gmail.com", password_hash=hash_password("Admin123!"),
                        full_name="Tizim administratori", role="ADMIN"))
        teachers = []
        for uname, name, dept in (("teacher1", "Karimov Anvar", "Axborot texnologiyalari"),
                                  ("teacher2", "Saidova Dilnoza", "Matematika")):
            u = User(username=uname, email=f"{uname}@univ.uz", password_hash=hash_password("Teacher123!"),
                     full_name=name, role="TEACHER")
            db.add(u)
            db.flush()
            t = Teacher(user_id=u.id, department=dept)
            db.add(t)
            db.flush()
            teachers.append(t)
        groups = []
        for i, name in enumerate(("DI-21-01", "DI-21-02", "DI-22-01")):
            g = Group(name=name, course_year=3 if i < 2 else 2, specialty="Dasturiy injiniring",
                      curator_id=teachers[i % 2].id)
            db.add(g)
            db.flush()
            groups.append(g)
        subjects = []
        for code, name, tidx in (("CS101", "Ma'lumotlar bazasi", 0), ("CS102", "Dasturlash asoslari", 1),
                                 ("MA101", "Diskret matematika", 1), ("EN101", "Ingliz tili", 0)):
            s = Subject(code=code, name=name, credits=4, semester=5, teacher_id=teachers[tidx].id)
            db.add(s)
            db.flush()
            subjects.append(s)

        today = date.today()
        n = 0
        for g in groups:
            for k in range(8):
                n += 1
                st = Student(student_code=f"S{n:03d}", full_name=f"{LAST[k]} {FIRST[(n * 3) % len(FIRST)]}",
                             email=f"s{n:03d}@student.uz", group_id=g.id)
                db.add(st)
                db.flush()
                start, end, p_att = PROFILES[rnd.randrange(len(PROFILES))]
                for sub in subjects:
                    enr = Enrollment(student_id=st.id, subject_id=sub.id)
                    db.add(enr)
                    db.flush()
                    for j in range(6):  # 6 ta baho, 60 kundan hozirgacha
                        score = start + (end - start) * j / 5 + rnd.uniform(-6, 6)
                        db.add(Grade(enrollment_id=enr.id, grade_type="MIDTERM" if j == 5 else "CURRENT",
                                     score=round(max(5, min(100, score)), 1), max_score=100,
                                     graded_at=today - timedelta(days=60 - j * 10), created_by=None))
                    for w in range(10):  # 10 ta dars
                        r = rnd.random()
                        status = "PRESENT" if r < p_att else ("LATE" if r < p_att + 0.05 else "ABSENT")
                        db.add(Attendance(enrollment_id=enr.id, lesson_date=today - timedelta(days=70 - w * 7),
                                          status=status))
        db.commit()
        print("Demo ma'lumotlar yaratildi. Risk hisoblanmoqda...")
        print(assess_all(db))
        print("Kirish: admin / Admin123!   teacher1 / Teacher123!   teacher2 / Teacher123!")


if __name__ == "__main__":
    run()
