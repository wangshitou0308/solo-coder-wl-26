import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_dashboard_as_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "director")
    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "daily_stats" in data
    assert "hall_occupancy" in data
    assert "cremation" in data
    assert "transport" in data


@pytest.mark.asyncio
async def test_dashboard_as_non_director(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_with_data(client: AsyncClient, test_users, test_deceased, test_halls):
    from datetime import datetime, timedelta

    headers_director = await get_auth_header(client, "director")
    headers_hall = await get_auth_header(client, "hall_admin")
    headers_cremation = await get_auth_header(client, "cremation_op")
    headers_transport = await get_auth_header(client, "hall_admin")

    now = datetime.utcnow()

    await client.post(
        "/api/v1/transport",
        headers=headers_transport,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )

    hall = test_halls[0]
    await client.post(
        "/api/v1/farewell/bookings",
        headers=headers_hall,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat()
        }
    )

    await client.post(
        "/api/v1/cremation",
        headers=headers_cremation,
        json={
            "deceased_id": test_deceased.id,
            "cremation_fee": 1500
        }
    )

    response = await client.get("/api/v1/dashboard", headers=headers_director)
    assert response.status_code == 200
    data = response.json()

    assert data["daily_stats"]["in_house_deceased"] >= 1
    assert len(data["hall_occupancy"]) >= 1
    assert data["cremation"]["total_in_queue"] >= 1
    assert data["transport"]["pending_tasks"] >= 1
