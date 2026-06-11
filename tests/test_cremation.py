import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_cremation(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deceased_id"] == test_deceased.id
    assert data["status"] == "queued"
    assert data["queue_position"] is not None


@pytest.mark.asyncio
async def test_urgent_cremation(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "is_urgent": True,
            "cremation_fee": 1500
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_urgent"] == True
    assert data["queue_position"] == 1


@pytest.mark.asyncio
async def test_start_cremation(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    create_response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    cremation_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/cremation/{cremation_id}/start",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["start_time"] is not None


@pytest.mark.asyncio
async def test_complete_cremation(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    create_response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    cremation_id = create_response.json()["id"]

    await client.post(f"/api/v1/cremation/{cremation_id}/start", headers=headers)

    response = await client.post(
        f"/api/v1/cremation/{cremation_id}/complete",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["end_time"] is not None


@pytest.mark.asyncio
async def test_collect_ashes(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    create_response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    cremation_id = create_response.json()["id"]

    await client.post(f"/api/v1/cremation/{cremation_id}/start", headers=headers)
    await client.post(f"/api/v1/cremation/{cremation_id}/complete", headers=headers)
    await client.post(f"/api/v1/cremation/{cremation_id}/ashes-ready", headers=headers)

    response = await client.post(
        f"/api/v1/cremation/{cremation_id}/collect-ashes",
        headers=headers,
        json={
            "ashes_receiver": "张三",
            "receiver_id_card": "110101198001011234",
            "receiver_phone": "13800000000",
            "relation_to_deceased": "儿子"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ashes_collected"
    assert data["ashes_receiver"] == "张三"
    assert data["collected_at"] is not None


@pytest.mark.asyncio
async def test_get_queue_position(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    create_response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    cremation_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/cremation/{cremation_id}/position",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "position" in data
    assert "total_in_queue" in data


@pytest.mark.asyncio
async def test_list_cremations(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )

    response = await client.get("/api/v1/cremation", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_auto_schedule_rejects_duplicate(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "cremation_op")

    create_response = await client.post(
        "/api/v1/cremation",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )
    assert create_response.status_code == 200

    auto_response = await client.post(
        f"/api/v1/cremation/auto-schedule/{test_deceased.id}",
        headers=headers
    )
    assert auto_response.status_code == 400
    assert "已在火化队列中" in auto_response.json()["detail"]

    headers_director = await get_auth_header(client, "director")
    await client.post(
        f"/api/v1/deceased/{test_deceased.id}/archive",
        headers=headers_director,
        json={"archived": True}
    )

    another_deceased_resp = await client.post(
        "/api/v1/deceased",
        headers=await get_auth_header(client, "hall_admin"),
        json={
            "name": "归档测试逝者",
            "gender": "女",
            "birth_date": "1940-05-05",
            "death_date": "2024-06-01",
            "id_card": "310101194005051234",
            "address": "测试地址B",
            "death_place": "测试地点B",
            "family_relations": []
        }
    )
    if another_deceased_resp.status_code == 200:
        archived_id = another_deceased_resp.json()["id"]
        await client.post(
            f"/api/v1/deceased/{archived_id}/archive",
            headers=headers_director,
            json={"archived": True}
        )
        archived_auto = await client.post(
            f"/api/v1/cremation/auto-schedule/{archived_id}",
            headers=headers
        )
        assert archived_auto.status_code == 400
        assert "已归档" in archived_auto.json()["detail"]
