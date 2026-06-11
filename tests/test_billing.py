import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_bill(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                },
                {
                    "fee_type": "cremation",
                    "item_name": "火化费",
                    "quantity": 1,
                    "unit_price": 1500
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deceased_id"] == test_deceased.id
    assert data["total_amount"] == 2300
    assert data["status"] == "unpaid"
    assert len(data["fee_items"]) == 2


@pytest.mark.asyncio
async def test_auto_generate_bill(client: AsyncClient, test_users, test_deceased, test_halls):
    from datetime import datetime, timedelta

    headers_hall = await get_auth_header(client, "hall_admin")
    headers_finance = await get_auth_header(client, "finance")
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
            "scheduled_time": (now + timedelta(hours=1)).isoformat()
        }
    )

    hall = test_halls[0]
    await client.post(
        "/api/v1/farewell/bookings",
        headers=headers_hall,
        json={
            "deceased_id": test_deceased.id,
            "hall_id": hall.id,
            "start_time": (now + timedelta(days=1, hours=9)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=11)).isoformat(),
            "require_photographer": True,
            "require_mc": True
        }
    )

    response = await client.post(
        f"/api/v1/billing/auto-generate/{test_deceased.id}",
        headers=headers_finance
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] > 0
    assert len(data["fee_items"]) >= 3


@pytest.mark.asyncio
async def test_process_payment(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    create_response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )
    bill_id = create_response.json()["id"]

    response = await client.post(
        "/api/v1/billing/pay",
        headers=headers,
        json={
            "bill_id": bill_id,
            "amount": 500,
            "payment_method": "cash"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 500
    assert data["payment_method"] == "cash"

    bill_response = await client.get(f"/api/v1/billing/{bill_id}", headers=headers)
    bill_data = bill_response.json()
    assert bill_data["paid_amount"] == 500
    assert bill_data["status"] == "partial_paid"


@pytest.mark.asyncio
async def test_full_payment(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    create_response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )
    bill_id = create_response.json()["id"]

    response = await client.post(
        "/api/v1/billing/pay",
        headers=headers,
        json={
            "bill_id": bill_id,
            "amount": 800,
            "payment_method": "wechat"
        }
    )
    assert response.status_code == 200

    bill_response = await client.get(f"/api/v1/billing/{bill_id}", headers=headers)
    bill_data = bill_response.json()
    assert bill_data["paid_amount"] == 800
    assert bill_data["status"] == "fully_paid"


@pytest.mark.asyncio
async def test_overpayment_rejected(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    create_response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )
    bill_id = create_response.json()["id"]

    response = await client.post(
        "/api/v1/billing/pay",
        headers=headers,
        json={
            "bill_id": bill_id,
            "amount": 1000,
            "payment_method": "cash"
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_fee_items(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    create_response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )
    bill_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/billing/{bill_id}/fee-items",
        headers=headers,
        json={
            "fee_items": [
                {
                    "fee_type": "service",
                    "item_name": "司仪服务费",
                    "quantity": 1,
                    "unit_price": 500
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] == 1300
    assert len(data["fee_items"]) == 2


@pytest.mark.asyncio
async def test_list_bills(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )

    response = await client.get("/api/v1/billing", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_negative_payment_rejected(client: AsyncClient, test_users, test_deceased):
    headers = await get_auth_header(client, "finance")

    create_response = await client.post(
        "/api/v1/billing",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "fee_items": [
                {
                    "fee_type": "transport",
                    "item_name": "遗体接运费",
                    "quantity": 1,
                    "unit_price": 800
                }
            ]
        }
    )
    bill_id = create_response.json()["id"]

    response = await client.post(
        "/api/v1/billing/pay",
        headers=headers,
        json={
            "bill_id": bill_id,
            "amount": -100,
            "payment_method": "cash"
        }
    )
    assert response.status_code == 422

    zero_response = await client.post(
        "/api/v1/billing/pay",
        headers=headers,
        json={
            "bill_id": bill_id,
            "amount": 0,
            "payment_method": "cash"
        }
    )
    assert zero_response.status_code == 422

    bill_response = await client.get(f"/api/v1/billing/{bill_id}", headers=headers)
    bill_data = bill_response.json()
    assert bill_data["paid_amount"] == 0
