"""ORM modellar. Jadval/ustun nomlari database/schema.sql bilan 1:1 mos."""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, SmallInteger, String, Text, UniqueConstraint, false, func, true)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

NUM = Numeric(5, 2, asdecimal=False)  # float qaytaradi (JSON uchun qulay)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('ADMIN','TEACHER')", name="ck_users_role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    course_year: Mapped[int] = mapped_column(SmallInteger)
    specialty: Mapped[str] = mapped_column(String(100))
    curator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE','LEAVE','EXPELLED')", name="ck_students_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_code: Mapped[str] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE", server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    credits: Mapped[int] = mapped_column(SmallInteger, default=3, server_default="3")
    semester: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), index=True)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_enrollment"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    enrolled_at: Mapped[date] = mapped_column(Date, default=date.today)


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint("grade_type IN ('CURRENT','MIDTERM','FINAL')", name="ck_grade_type"),
        CheckConstraint("score >= 0 AND score <= max_score", name="ck_grade_range"),
        Index("idx_grades_enrollment", "enrollment_id", "graded_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    grade_type: Mapped[str] = mapped_column(String(10), default="CURRENT", server_default="CURRENT")
    score: Mapped[float] = mapped_column(NUM)
    max_score: Mapped[float] = mapped_column(NUM, default=100, server_default="100")
    graded_at: Mapped[date] = mapped_column(Date, default=date.today)
    comment: Mapped[Optional[str]] = mapped_column(String(255))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "lesson_date", name="uq_attendance"),
        CheckConstraint("status IN ('PRESENT','ABSENT','LATE','EXCUSED')", name="ck_attendance_status"),
        Index("idx_attendance_enrollment", "enrollment_id", "lesson_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    lesson_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="PRESENT", server_default="PRESENT")
    note: Mapped[Optional[str]] = mapped_column(String(255))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_risk_level"),
        Index("idx_risk_student_time", "student_id", "calculated_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    avg_score: Mapped[Optional[float]] = mapped_column(NUM)
    attendance_rate: Mapped[Optional[float]] = mapped_column(NUM)
    trend_score: Mapped[float] = mapped_column(NUM, default=0, server_default="0")
    risk_score: Mapped[float] = mapped_column(NUM)
    risk_level: Mapped[str] = mapped_column(String(10), index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("channel IN ('IN_APP','EMAIL')", name="ck_notif_channel"),
        CheckConstraint("status IN ('PENDING','SENT','FAILED')", name="ck_notif_status"),
        Index("idx_notif_recipient", "recipient_user_id", "is_read"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    risk_assessment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("risk_assessments.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10), default="IN_APP", server_default="IN_APP")
    status: Mapped[str] = mapped_column(String(10), default="PENDING", server_default="PENDING")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
