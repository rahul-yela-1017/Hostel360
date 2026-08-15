import os
from pathlib import Path
from datetime import date, timedelta

TEST_DB = Path(__file__).resolve().parents[1] / "smart_hostel_test.db"
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["KIOSK_API_KEY"] = "test-kiosk-key"
os.environ["DEMO_MODE"] = "false"

import pytest
from fastapi.testclient import TestClient
from app.main import app

ADMIN_EMAIL = "admin@mrbh.edu.in"
ADMIN_PASSWORD = "Admin#2026Secure"


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def admin_headers(client):
    status = client.get("/api/auth/setup/status")
    assert status.status_code == 200
    assert status.json()["setup_required"] is True
    response = client.post("/api/auth/setup/admin", json={
        "name": "Hostel Administrator", "email": ADMIN_EMAIL,
        "phone": "9000000000", "password": ADMIN_PASSWORD,
    })
    assert response.status_code == 201, response.text
    return login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def staff(client, admin_headers):
    warden_temp = "Warden#2026Temp"
    cook_temp = "Cook#2026TempPwd"
    warden = client.post("/api/admin/wardens", headers=admin_headers, json={
        "name": "Main Warden", "email": "warden@mrbh.edu.in", "phone": "9000000001",
        "employee_id": "W-001", "designation": "Senior Warden", "assigned_area": "Day shift",
        "hostel_id": 1, "temporary_password": warden_temp,
    })
    cook = client.post("/api/admin/cooks", headers=admin_headers, json={
        "name": "Main Cook", "email": "cook@mrbh.edu.in", "phone": "9000000002",
        "employee_id": "C-001", "assigned_area": "Main Mess", "hostel_id": 1,
        "temporary_password": cook_temp,
    })
    assert warden.status_code == 201 and cook.status_code == 201
    warden_headers = login(client, "warden@mrbh.edu.in", warden_temp)
    cook_headers = login(client, "cook@mrbh.edu.in", cook_temp)
    assert client.get("/api/warden/rooms", headers=warden_headers).status_code == 403
    assert client.post("/api/auth/change-password", headers=warden_headers,
                       json={"current_password": warden_temp, "new_password": "Warden#2026Private"}).status_code == 200
    assert client.post("/api/auth/change-password", headers=cook_headers,
                       json={"current_password": cook_temp, "new_password": "Cook#2026PrivatePwd"}).status_code == 200
    return {"warden": warden_headers, "cook": cook_headers}


@pytest.fixture(scope="module")
def student(client, admin_headers):
    temp = "MRBH@Student2026"
    payload = {
        "full_name": "Real Student", "roll_no": "MRBH-0001", "phone": "9000000003",
        "email": "student@mrbh.edu.in", "course": "B.Tech", "branch": "CSE", "year": 1,
        "parent_name": "Student Guardian", "parent_phone": "9000000004",
        "emergency_contact": "9000000005", "student_id": "STU-0001", "hostel_id": 1,
        "room_number": 204, "bed_number": 1,
    }
    response = client.post("/api/warden/students", headers=admin_headers, json=payload)
    assert response.status_code == 201, response.text
    headers = login(client, "student@mrbh.edu.in", temp)
    assert client.get("/api/student/profile", headers=headers).status_code == 403
    assert client.post("/api/auth/change-password", headers=headers,
                       json={"current_password": temp, "new_password": "Student#2026Private"}).status_code == 200
    return {"id": response.json()["id"], "headers": headers, "payload": payload}


def test_clean_first_run_and_room_invariants(client, admin_headers):
    status = client.get("/api/auth/setup/status").json()
    assert status == {"setup_required": False, "hostel_name": "Malla Reddy Boys Hostel"}
    summary = client.get("/api/dashboard/summary", headers=admin_headers).json()
    assert summary["total_rooms"] == 431
    assert summary["total_beds"] == 1724
    assert summary["total_students"] == 0
    assert summary["occupied_beds"] == 0
    room = client.get("/api/warden/rooms/430", headers=admin_headers).json()
    assert room["capacity"] == 4
    assert room["status"] == "EMPTY"
    assert [bed["bed_number"] for bed in room["beds"]] == [1, 2, 3, 4]


def test_initial_admin_setup_is_one_time(client, admin_headers):
    response = client.post("/api/auth/setup/admin", json={
        "name": "Second Admin", "email": "second@mrbh.edu.in", "phone": "9111111111",
        "password": "Second#Admin2026",
    })
    assert response.status_code == 409


def test_backend_role_restrictions(client, staff):
    assert client.get("/api/reports/rooms/download", headers=staff["cook"]).status_code == 403
    assert client.get("/api/warden/students", headers=staff["cook"]).status_code == 403
    assert client.get("/api/warden/rooms", headers=staff["warden"]).status_code == 200


def test_student_creation_and_atomic_bed_assignment(client, admin_headers, student):
    room = client.get("/api/warden/rooms/204", headers=admin_headers).json()
    assert room["occupied"] == 1
    assert room["beds"][0]["student"]["name"] == "Real Student"
    assert client.get("/api/student/profile", headers=student["headers"]).json()["room"] == 204


def test_occupied_bed_conflict_rolls_back_student(client, admin_headers, student):
    payload = dict(student["payload"])
    payload.update({"full_name": "Conflicting Student", "roll_no": "MRBH-0002",
                    "email": "conflict@mrbh.edu.in", "student_id": "STU-0002"})
    response = client.post("/api/warden/students", headers=admin_headers, json=payload)
    assert response.status_code == 409
    search = client.get("/api/warden/students?q=Conflicting", headers=admin_headers).json()
    assert search["total"] == 0


def test_cook_publishes_menu_directly_to_student(client, staff, student):
    payload = {
        "menu_date": str(date.today()), "breakfast": "Idly · Sambar", "lunch": "Rice · Dal",
        "snacks": "Tea · Biscuits", "dinner": "Roti · Paneer", "hostel_id": 1, "publish": True,
    }
    published = client.put("/api/cook/menu", headers=staff["cook"], json=payload)
    assert published.status_code == 200
    visible = client.get("/api/menu/today", headers=student["headers"])
    assert visible.status_code == 200
    assert visible.json()["dinner"] == "Roti · Paneer"


def test_manual_attendance_appears_on_student_dashboard(client, admin_headers, student):
    target = date.today() - timedelta(days=1)
    marked = client.post("/api/attendance/mark", headers=admin_headers, json={
        "student_id": student["id"], "attendance_date": str(target),
        "attendance_time": "20:15:00", "status": "PRESENT",
    })
    assert marked.status_code == 200, marked.text
    own = client.get("/api/student/attendance", headers=student["headers"])
    assert own.status_code == 200
    assert any(row["date"] == str(target) and row["status"] == "PRESENT" for row in own.json()["history"])


def test_face_attendance_and_duplicate_protection(client, admin_headers, student):
    vector = [0.01 * ((i % 7) + 1) for i in range(128)]
    enrolled = client.post("/api/face/enroll", headers=admin_headers, json={
        "student_id": student["id"], "embedding": vector,
        "model_version": "test-provider-v1", "liveness_score": .99,
    })
    assert enrolled.status_code == 200
    request = {"device_id": "GATE-01", "embedding": vector, "liveness_score": .99,
               "captured_at": f"{date.today()}T20:00:00+05:30"}
    kiosk_headers = {"X-Kiosk-Key": "test-kiosk-key"}
    first = client.post("/api/face/recognize", headers=kiosk_headers, json=request)
    second = client.post("/api/face/recognize", headers=kiosk_headers, json=request)
    assert first.status_code == 200 and first.json()["result"] == "RECORDED"
    assert second.status_code == 200 and second.json()["result"] == "ALREADY_RECORDED"


def test_secure_room_report(client, admin_headers):
    response = client.get("/api/reports/rooms/download?room_from=200&room_to=204&format=zip", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content.startswith(b"PK")
