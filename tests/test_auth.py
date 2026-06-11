import pytest
from httpx import AsyncClient

from app.core.roles import UserRole
from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "director", "password": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_users):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "director", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient, test_users):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "123456"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "director"
    assert data["role"] == UserRole.DIRECTOR.value


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": "123456", "new_password": "654321"}
    )
    assert response.status_code == 200

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "director", "password": "654321"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": "wrong", "new_password": "654321"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_user_as_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={
            "username": "new_user",
            "full_name": "新用户",
            "password": "123456",
            "role": UserRole.HALL_ADMIN.value
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "new_user"


@pytest.mark.asyncio
async def test_create_user_as_non_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.post(
        "/api/v1/auth/users",
        headers=headers,
        json={
            "username": "new_user2",
            "full_name": "新用户2",
            "password": "123456",
            "role": UserRole.HALL_ADMIN.value
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.get("/api/v1/auth/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6


@pytest.mark.asyncio
async def test_list_users_as_non_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.get("/api/v1/auth/users", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_drivers_list(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.get("/api/v1/auth/users/drivers", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for driver in data:
        assert driver["role"] == UserRole.DRIVER.value
