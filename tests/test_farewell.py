import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_hall_as_hall_admin(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.post(
        "/api/v1/farewell/halls",
        headers=headers,
        json={
            "name": "新测试厅",
            "level": "standard",
            "capacity": 50,
            "hourly_rate": 500
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "新测试厅"


@pytest.mark.asyncio
async def test_list_halls(client: AsyncClient, test_users, test_halls):
    headers = await get_auth_header(client, "hall_admin")
    response = await client.get("/api/v1/farewell/halls", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_check_time_slot_available(client: AsyncClient, test_users, test_halls):
    headers = await get_auth_header(client, "hall_admin")
    hall = test_halls[0]
    now = datetime.utcnow()

    response = await client.post(
        "/api/v1/farewell/check-slot",
        headers=headers,
        json={
            "hall_id": hall.id,
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=2)).isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] == False


@pytest.mark.asyncio
async def test_create_booking(client: AsyncClient, test_users, test_halls, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    hall = test_halls[0]
    now = datetime.utcnow()
    start = now + timedelta(days=1, hours=9)
    end = now + timedelta(days=1, hours=11)

    response = await client.post(
        "/api/v1/farewell/bookings",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "decoration_type": "flowers",
            "require_photographer": True,
            "require_mc": True,
            "services": [
                {"service_name": "鲜花布置", "quantity": 2, "unit_price": 300}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hall_id"] == hall.id
    assert data["total_amount"] > 0
    assert len(data["services"]) == 1


@pytest.mark.asyncio
async def test_create_booking_conflict(client: AsyncClient, test_users, test_halls, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    hall = test_halls[0]
    now = datetime.utcnow()
    start = now + timedelta(days=1, hours=9)
    end = now + timedelta(days=1, hours=11)

    await client.post(
        "/api/v1/farewell/bookings",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }
    )

    response = await client.post(
        "/api/v1/farewell/bookings",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_bookings(client: AsyncClient, test_users, test_halls, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    hall = test_halls[0]
    now = datetime.utcnow()

    await client.post(
        "/api/v1/farewell/bookings",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=2)).isoformat()
        }
    )

    response = await client.get("/api/v1/farewell/bookings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_cancel_booking(client: AsyncClient, test_users, test_halls, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    hall = test_halls[0]
    now = datetime.utcnow()

    create_response = await client.post(
        "/api/v1/farewell/bookings",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=2)).isoformat()
        }
    )
    booking_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/farewell/bookings/{booking_id}/cancel",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
