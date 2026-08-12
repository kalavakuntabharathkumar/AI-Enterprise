import os

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def token(email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def auth(value):
    return {"Authorization": f"Bearer {value}"}


def test_login_success():
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).status_code == 200


def test_login_wrong_password():
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"}).status_code == 401


def test_login_unknown_user():
    assert client.post("/api/auth/login", json={"email": "none@example.com", "password": "wrong"}).status_code == 401


def test_projects_without_token():
    assert client.get("/api/projects").status_code == 401


def test_invalid_token():
    assert client.get("/api/projects", headers=auth("bad")).status_code == 401


def test_admin_me():
    assert client.get("/api/auth/me", headers=auth(token("admin@example.com", "admin123"))).status_code == 200


def test_employee_can_read_projects():
    assert client.get("/api/projects", headers=auth(token("employee@example.com", "employee123"))).status_code == 200


def test_employee_cannot_create_project():
    assert client.post("/api/projects", headers=auth(token("employee@example.com", "employee123")), json={"name": "X"}).status_code == 403


def test_manager_can_create_project():
    assert client.post("/api/projects", headers=auth(token("manager@example.com", "manager123")), json={"name": "Test", "status": "active"}).status_code == 201


def test_employee_cannot_delete_task():
    assert client.delete("/api/tasks/1", headers=auth(token("employee@example.com", "employee123"))).status_code == 403


def test_manager_cannot_delete_task():
    assert client.delete("/api/tasks/1", headers=auth(token("manager@example.com", "manager123"))).status_code == 403


def test_missing_project():
    assert client.get("/api/projects/99999", headers=auth(token("employee@example.com", "employee123"))).status_code == 404


def test_missing_task():
    assert client.get("/api/tasks/99999", headers=auth(token("employee@example.com", "employee123"))).status_code == 404


def test_list_employees():
    assert client.get("/api/employees", headers=auth(token("admin@example.com", "admin123"))).status_code == 200


def test_list_tasks():
    assert client.get("/api/tasks", headers=auth(token("employee@example.com", "employee123"))).status_code == 200


def test_update_project():
    t = token("manager@example.com", "manager123")
    assert client.put("/api/projects/1", headers=auth(t), json={"status": "completed"}).status_code == 200


def test_update_task():
    t = token("manager@example.com", "manager123")
    assert client.put("/api/tasks/1", headers=auth(t), json={"priority": "high"}).status_code == 200


def test_create_task():
    t = token("manager@example.com", "manager123")
    assert client.post("/api/tasks", headers=auth(t), json={"title": "Test task", "status": "todo", "priority": "low", "project_id": 1, "assignee_id": 3}).status_code == 201


def test_copilot_without_key():
    os.environ.pop("OPENAI_API_KEY", None)
    t = token("employee@example.com", "employee123")
    r = client.post("/api/copilot", headers=auth(t), json={"question": "Summarize workload"})
    assert r.status_code == 200 and "Demo mode" in r.json()["answer"]


def test_copilot_empty_question():
    t = token("employee@example.com", "employee123")
    assert client.post("/api/copilot", headers=auth(t), json={"question": ""}).status_code == 422
