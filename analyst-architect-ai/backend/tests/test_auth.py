"""
Tests for authentication, JWT, and role-based access control.
Uses the session-scoped `client` fixture from conftest.py (users pre-seeded).
"""
import pytest


# ─── Login ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_admin_success(client):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert data["username"] == "admin"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/auth/login", data={"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_analyst_and_architect(client):
    for username, password in [("analyst", "analyst123"), ("architect", "architect123")]:
        resp = await client.post("/auth/login", data={"username": username, "password": password})
        assert resp.status_code == 200
        assert resp.json()["username"] == username


# ─── /auth/me ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_requires_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile(client):
    login = await client.post("/auth/login", data={"username": "analyst", "password": "analyst123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "analyst"
    assert resp.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_me_rejects_garbage_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


# ─── RBAC: admin-only endpoints ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_requires_admin(client):
    # Analyst should be forbidden
    login = await client.post("/auth/login", data={"username": "analyst", "password": "analyst123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_admin(client):
    login = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()}
    assert {"admin", "analyst", "architect"}.issubset(usernames)


@pytest.mark.asyncio
async def test_architect_cannot_manage_users(client):
    login = await client.post("/auth/login", data={"username": "architect", "password": "architect123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ─── User lifecycle: register / update / reset password / block ────────────

@pytest.mark.asyncio
async def test_full_user_lifecycle(client):
    login = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    admin_token = login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register
    reg = await client.post("/auth/register", headers=admin_headers, json={
        "username": "lifecycle_user",
        "email": "lifecycle@test.com",
        "password": "initial123",
        "full_name": "Lifecycle Test",
        "role": "analyst",
    })
    assert reg.status_code == 200
    user_id = reg.json()["id"]
    assert reg.json()["role"] == "analyst"

    # Duplicate username rejected
    dup = await client.post("/auth/register", headers=admin_headers, json={
        "username": "lifecycle_user",
        "email": "other@test.com",
        "password": "initial123",
        "role": "analyst",
    })
    assert dup.status_code == 400

    # Update role
    upd = await client.patch(f"/auth/users/{user_id}", headers=admin_headers, json={"role": "architect"})
    assert upd.status_code == 200
    assert upd.json()["role"] == "architect"

    # New user can log in
    login2 = await client.post("/auth/login", data={"username": "lifecycle_user", "password": "initial123"})
    assert login2.status_code == 200

    # Reset password
    reset = await client.post(
        f"/auth/users/{user_id}/reset-password",
        headers=admin_headers,
        json={"new_password": "newpassword456"},
    )
    assert reset.status_code == 200

    # Old password no longer works
    old_login = await client.post("/auth/login", data={"username": "lifecycle_user", "password": "initial123"})
    assert old_login.status_code == 401

    # New password works
    new_login = await client.post("/auth/login", data={"username": "lifecycle_user", "password": "newpassword456"})
    assert new_login.status_code == 200

    # Block user
    block = await client.patch(f"/auth/users/{user_id}", headers=admin_headers, json={"is_active": False})
    assert block.status_code == 200
    assert block.json()["is_active"] is False

    # Blocked user cannot log in
    blocked_login = await client.post("/auth/login", data={"username": "lifecycle_user", "password": "newpassword456"})
    assert blocked_login.status_code == 401


@pytest.mark.asyncio
async def test_update_user_requires_admin(client):
    login = await client.post("/auth/login", data={"username": "analyst", "password": "analyst123"})
    token = login.json()["access_token"]
    resp = await client.patch(
        "/auth/users/some-fake-id",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_requires_admin(client):
    login = await client.post("/auth/login", data={"username": "architect", "password": "architect123"})
    token = login.json()["access_token"]
    resp = await client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "sneaky", "email": "s@test.com", "password": "pass123", "role": "admin"},
    )
    assert resp.status_code == 403


# ─── Protected feature endpoints work with valid token ──────────────────────

@pytest.mark.asyncio
async def test_documents_accessible_with_any_role(client):
    for username, password in [("admin", "admin123"), ("analyst", "analyst123"), ("architect", "architect123")]:
        login = await client.post("/auth/login", data={"username": username, "password": password})
        token = login.json()["access_token"]
        resp = await client.get("/documents", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
