"""Pydantic sxemalar (kirish/chiqish validatsiyasi)."""
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
GradeType = Literal["CURRENT", "MIDTERM", "FINAL"]
AttendanceStatus = Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORM):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(pattern=EMAIL_RE, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=3, max_length=120)
    role: Literal["ADMIN", "TEACHER"] = "TEACHER"
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=72)


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=30)
    course_year: int = Field(ge=1, le=6)
    specialty: str = Field(min_length=2, max_length=100)
    curator_id: Optional[int] = None


class SubjectIn(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=120)
    credits: int = Field(3, ge=1, le=30)
    semester: int = Field(1, ge=1, le=12)
    teacher_id: Optional[int] = None


class StudentIn(BaseModel):
    student_code: str = Field(min_length=3, max_length=20)
    full_name: str = Field(min_length=3, max_length=120)
    email: Optional[str] = Field(None, pattern=EMAIL_RE, max_length=120)
    phone: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    group_id: int
    status: Literal["ACTIVE", "LEAVE", "EXPELLED"] = "ACTIVE"


class EnrollmentIn(BaseModel):
    student_id: int
    subject_id: int


class GroupEnrollIn(BaseModel):
    group_id: int
    subject_id: int


class GradeIn(BaseModel):
    enrollment_id: int
    grade_type: GradeType = "CURRENT"
    score: float = Field(ge=0)
    max_score: float = Field(100, gt=0)
    graded_at: Optional[date] = None
    comment: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def _score_in_range(self):
        if self.score > self.max_score:
            raise ValueError("Ball maksimal balldan oshmasligi kerak")
        return self


class AttendanceRecord(BaseModel):
    enrollment_id: int
    status: AttendanceStatus = "PRESENT"
    note: Optional[str] = Field(None, max_length=255)


class AttendanceBulkIn(BaseModel):
    subject_id: int
    lesson_date: date
    records: List[AttendanceRecord] = Field(min_length=1)
