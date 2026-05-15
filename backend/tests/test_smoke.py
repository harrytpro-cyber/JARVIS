"""
Smoke tests — vérifie que tous les endpoints critiques répondent.

Prérequis : backend + postgres + redis démarrés (make start).
Lance avec : pytest tests/test_smoke.py -v
"""
import os
import uuid
import pytest
import httpx

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")

# Compte de test créé à la volée et supprimé après
TEST_EMAIL    = f"smoke_{uuid.uuid4().hex[:8]}@test.local"
TEST_PASSWORD = "SmokePwd123!"
TEST_USERNAME = f"smoke_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    """Inscrit un utilisateur de test et retourne les headers JWT."""
    r = client.post("/api/v1/auth/register", json={
        "email": TEST_EMAIL,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "full_name": "Smoke Test",
    })
    assert r.status_code in (201, 409), f"Register failed: {r.text}"

    r = client.post("/api/v1/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── 1. Health ─────────────────────────────────────────────────────
class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_status_field(self, client):
        r = client.get("/health")
        data = r.json()
        assert "status" in data
        assert data["status"] in ("online", "degraded")

    def test_health_reports_services(self, client):
        r = client.get("/health")
        data = r.json()
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]


# ── 2. Auth ───────────────────────────────────────────────────────
class TestAuth:
    def test_register_and_login(self, client):
        email = f"smoke2_{uuid.uuid4().hex[:8]}@test.local"
        r = client.post("/api/v1/auth/register", json={
            "email": email,
            "username": f"u_{uuid.uuid4().hex[:6]}",
            "password": "TestPwd456!",
        })
        assert r.status_code == 201
        r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPwd456!"})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    def test_login_wrong_password(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": TEST_EMAIL, "password": "wrong",
        })
        assert r.status_code == 401

    def test_me_with_valid_token(self, client, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == TEST_EMAIL

    def test_me_without_token(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 403


# ── 3. Chat ───────────────────────────────────────────────────────
class TestChat:
    def test_stream_requires_auth(self, client):
        r = client.get("/api/v1/chat/stream", params={"content": "test"})
        assert r.status_code == 403

    def test_stream_returns_sse(self, client, auth_headers):
        with client.stream("GET", "/api/v1/chat/stream",
                           params={"content": "Dis juste 'OK'"},
                           headers=auth_headers) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers.get("content-type", "")

    def test_list_conversations(self, client, auth_headers):
        r = client.get("/api/v1/chat/conversations", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── 4. Mémoire ────────────────────────────────────────────────────
class TestMemory:
    def test_list_memories_empty(self, client, auth_headers):
        r = client.get("/api/v1/memory/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_save_and_list_memory(self, client, auth_headers):
        r = client.post("/api/v1/memory/", headers=auth_headers, json={
            "content": "Test smoke memory",
            "memory_type": "fact",
            "importance": 0.5,
        })
        assert r.status_code in (200, 201)
        r2 = client.get("/api/v1/memory/", headers=auth_headers)
        contents = [m["content"] for m in r2.json()]
        assert any("smoke" in c for c in contents)

    def test_session_memory(self, client, auth_headers):
        r = client.get("/api/v1/memory/session", headers=auth_headers)
        assert r.status_code == 200


# ── 5. Tâches ─────────────────────────────────────────────────────
class TestTasks:
    def test_list_tasks(self, client, auth_headers):
        r = client.get("/api/v1/tasks/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_task(self, client, auth_headers):
        r = client.post("/api/v1/tasks/", headers=auth_headers, json={
            "title": "Tâche smoke test",
            "priority": "normale",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Tâche smoke test"
        return data["id"]

    def test_update_task(self, client, auth_headers):
        r = client.post("/api/v1/tasks/", headers=auth_headers, json={
            "title": "À compléter", "priority": "basse",
        })
        task_id = r.json()["id"]
        r2 = client.patch(f"/api/v1/tasks/{task_id}", headers=auth_headers,
                          json={"status": "done"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "done"

    def test_delete_task(self, client, auth_headers):
        r = client.post("/api/v1/tasks/", headers=auth_headers, json={
            "title": "À supprimer", "priority": "basse",
        })
        task_id = r.json()["id"]
        r2 = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert r2.status_code == 204


# ── 6. Stats système ──────────────────────────────────────────────
class TestSystem:
    def test_stats_returns_200(self, client, auth_headers):
        r = client.get("/api/v1/system/stats", headers=auth_headers)
        assert r.status_code == 200

    def test_stats_has_cpu_and_ram(self, client, auth_headers):
        r = client.get("/api/v1/system/stats", headers=auth_headers)
        data = r.json()
        assert "cpu_percent" in data
        assert "ram_percent" in data
        assert "disk_percent" in data
        assert 0 <= data["cpu_percent"] <= 100
        assert 0 <= data["ram_percent"] <= 100


# ── 7. Projets ────────────────────────────────────────────────────
class TestProjects:
    def test_list_projects(self, client, auth_headers):
        r = client.get("/api/v1/projects/", headers=auth_headers)
        assert r.status_code == 200

    def test_create_project(self, client, auth_headers):
        r = client.post("/api/v1/projects/", headers=auth_headers, json={
            "name": "Projet smoke test",
            "description": "Test automatisé",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Projet smoke test"


# ── 8. Endpoints protégés sans token ─────────────────────────────
class TestAuthRequired:
    @pytest.mark.parametrize("method,path", [
        ("GET",  "/api/v1/tasks/"),
        ("GET",  "/api/v1/memory/"),
        ("GET",  "/api/v1/system/stats"),
        ("GET",  "/api/v1/projects/"),
        ("GET",  "/api/v1/briefing/morning"),
    ])
    def test_protected_routes_require_auth(self, client, method, path):
        r = client.request(method, path)
        assert r.status_code in (401, 403), f"{method} {path} devrait retourner 401/403, got {r.status_code}"
