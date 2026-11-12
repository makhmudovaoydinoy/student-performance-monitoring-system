"""Integratsion testlar (SQLite, FastAPI TestClient). Ishga tushirish: cd backend && pytest"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, username, password):
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_fail_and_protected(client):
    assert client.post("/api/auth/login", data={"username": "admin", "password": "xato"}).status_code == 401
    assert client.get("/api/students").status_code == 401


def test_full_flow(client):
    admin = login(client, "admin", "Admin123!")
    # o'qituvchi
    r = client.post("/api/users", headers=admin, json={
        "username": "t1", "email": "t1@univ.uz", "password": "Teacher123!", "full_name": "Test Teacher", "role": "TEACHER"})
    assert r.status_code == 201, r.text
    teacher_id = client.get("/api/teachers", headers=admin).json()[0]["id"]
    # guruh, fan, talaba, enrollment
    g = client.post("/api/groups", headers=admin, json={"name": "T-01", "course_year": 2, "specialty": "IT", "curator_id": teacher_id})
    assert g.status_code == 201, g.text
    s = client.post("/api/subjects", headers=admin, json={"code": "T101", "name": "Test fan", "teacher_id": teacher_id})
    assert s.status_code == 201, s.text
    st = client.post("/api/students", headers=admin, json={"student_code": "T001", "full_name": "Test Talaba", "group_id": g.json()["id"]})
    assert st.status_code == 201, st.text
    en = client.post("/api/enrollments", headers=admin, json={"student_id": st.json()["id"], "subject_id": s.json()["id"]})
    assert en.status_code == 201, en.text
    assert client.post("/api/enrollments", headers=admin, json={"student_id": st.json()["id"], "subject_id": s.json()["id"]}).status_code == 409

    teacher = login(client, "t1", "Teacher123!")
    # o'qituvchi talaba qo'sha olmaydi (RBAC)
    assert client.post("/api/students", headers=teacher, json={"student_code": "X", "full_name": "Xxx", "group_id": 1}).status_code == 403
    # past baholar -> xavf
    for score in (30, 25, 20):
        r = client.post("/api/grades", headers=teacher, json={"enrollment_id": en.json()["id"], "score": score})
        assert r.status_code == 201, r.text
    client.post("/api/attendance/bulk", headers=teacher, json={
        "subject_id": s.json()["id"], "lesson_date": "2025-01-10",
        "records": [{"enrollment_id": en.json()["id"], "status": "ABSENT"}]})
    risky = client.get("/api/risk/at-risk", headers=teacher).json()
    assert len(risky) == 1 and risky[0]["risk_level"] in ("HIGH", "CRITICAL")
    # xabarnoma yaratilgan
    notes = client.get("/api/notifications", headers=teacher).json()
    assert len(notes) >= 1
    # dashboard va scheduler
    assert client.get("/api/dashboard/summary", headers=admin).json()["totals"]["at_risk"] == 1
    assert client.post("/api/risk/scheduler-run", headers={"X-Scheduler-Token": "yomon"}).status_code == 403
    assert client.post("/api/risk/scheduler-run", headers={"X-Scheduler-Token": "sched-token"}).status_code == 200
