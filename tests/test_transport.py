import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_transport_order(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    now = datetime.utcnow()

    response = await client.post(
        "/api/v1/transport",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deceased_id"] == test_deceased.id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_assign_driver(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    driver_user = test_users["driver1"]
    now = datetime.utcnow()

    create_response = await client.post(
        "/api/v1/transport",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    order_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/transport/{order_id}/assign-driver",
        headers=headers,
        json={
            "driver_id": driver_user.id,
            "vehicle_number": "京A·12345"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == driver_user.id
    assert data["status"] == "assigned"


@pytest.mark.asyncio
async def test_driver_update_status(client: AsyncClient, test_users, test_deceased):
    headers_admin = await get_auth_header(client, "hall_admin")
    driver_user = test_users["driver1"]
    now = datetime.utcnow()

    create_response = await client.post(
        "/api/v1/transport",
        headers=headers_admin,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    order_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/transport/{order_id}/assign-driver",
        headers=headers_admin,
        json={"driver_id": driver_user.id}
    )

    headers_driver = await get_auth_header(client, "driver1")
    response = await client.post(
        f"/api/v1/transport/{order_id}/status",
        headers=headers_driver,
        json={
            "status": "in_progress",
            "actual_pickup_time": now.isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_driver_tasks(client: AsyncClient, test_users, test_deceased):
    headers_admin = await get_auth_header(client, "hall_admin")
    driver_user = test_users["driver1"]
    now = datetime.utcnow()

    create_response = await client.post(
        "/api/v1/transport",
        headers=headers_admin,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    order_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/transport/{order_id}/assign-driver",
        headers=headers_admin,
        json={"driver_id": driver_user.id}
    )

    headers_driver = await get_auth_header(client, "driver1")
    response = await client.get("/api/v1/transport/my-tasks", headers=headers_driver)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_transport_orders(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "hall_admin")
    now = datetime.utcnow()

    await client.post(
        "/api/v1/transport",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "pickup_address": "测试医院",
            "pickup_contact": "测试家属",
            "pickup_phone": "13800000000",
            "scheduled_time": (now + timedelta(hours=2)).isoformat()
        }
    )

    response = await client.get("/api/v1/transport", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
