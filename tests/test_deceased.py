import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_deceased_as_hall_admin(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    family_user = test_users["family1"]

    response = await client.post(
        "/api/v1/deceased",
        headers=headers,
        json={
            "name": "测试逝者",
            "gender": "男",
            "birth_date": "1950-01-01",
            "death_date": "2024-01-01",
            "id_card": "110101195001011234",
            "address": "测试地址",
            "death_place": "测试地点",
            "family_relations": [
                {
                    "user_id": family_user.id,
                    "relation": "儿子",
                    "contact_phone": family_user.phone,
                    "is_primary": 1
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试逝者"
    assert len(data["family_relations"]) == 1


@pytest.mark.asyncio
async def test_create_deceased_invalid_id_card(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    family_user = test_users["family1"]

    response = await client.post(
        "/api/v1/deceased",
        headers=headers,
        json={
            "name": "测试逝者",
            "gender": "男",
            "birth_date": "1950-01-01",
            "death_date": "2024-01-01",
            "id_card": "123",
            "address": "测试地址",
            "death_place": "测试地点",
            "family_relations": [
                {
                    "user_id": family_user.id,
                    "relation": "儿子",
                    "contact_phone": family_user.phone,
                    "is_primary": 1
                }
            ]
        }
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_deceased_as_non_admin(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "family1")
    family_user = test_users["family1"]

    response = await client.post(
        "/api/v1/deceased",
        headers=headers,
        json={
            "name": "测试逝者",
            "gender": "男",
            "birth_date": "1950-01-01",
            "death_date": "2024-01-01",
            "id_card": "110101195001011234",
            "address": "测试地址",
            "death_place": "测试地点",
            "family_relations": [
                {
                    "user_id": family_user.id,
                    "relation": "儿子",
                    "contact_phone": family_user.phone,
                    "is_primary": 1
                }
            ]
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_deceased(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.get("/api/v1/deceased", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_deceased_as_family_member(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "family1")
    response = await client.get(f"/api/v1/deceased/{test_deceased.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_deceased.name


@pytest.mark.asyncio
async def test_update_deceased(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.put(
        f"/api/v1/deceased/{test_deceased.id}",
        headers=headers,
        json={"remark": "更新备注"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["remark"] == "更新备注"


@pytest.mark.asyncio
async def test_archive_deceased(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "director")
    response = await client.post(
        f"/api/v1/deceased/{test_deceased.id}/archive",
        headers=headers,
        json={"archived": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_archived"] == True

    headers_admin = await get_auth_header(client, "hall_admin")
    response = await client.put(
        f"/api/v1/deceased/{test_deceased.id}",
        headers=headers_admin,
        json={"remark": "尝试更新归档档案"}
    )
    assert response.status_code == 400
