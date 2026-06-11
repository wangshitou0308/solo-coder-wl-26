import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, test_users):
    headers = await get_auth_header(client, "finance")

    response = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": "测试商品",
            "category": "urn",
            "price": 5000,
            "stock_quantity": 10
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试商品"
    assert data["stock_quantity"] == 10


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, test_users, test_products):
    headers = await get_auth_header(client, "family1")
    response = await client.get("/api/v1/products", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_create_product_order(client: AsyncClient, test_users, test_deceased, test_products):
    headers = await get_auth_header(client, "family1")
    product1 = test_products[0]
    product2 = test_products[1]

    initial_stock1 = product1.stock_quantity
    initial_stock2 = product2.stock_quantity

    response = await client.post(
        "/api/v1/products/orders",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "items": [
                {"product_id": product1.id, "quantity": 1},
                {"product_id": product2.id, "quantity": 2}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deceased_id"] == test_deceased.id
    assert len(data["items"]) == 2
    assert data["total_amount"] == product1.price + product2.price * 2

    headers_admin = await get_auth_header(client, "finance")
    product1_response = await client.get(f"/api/v1/products/{product1.id}", headers=headers_admin)
    product2_response = await client.get(f"/api/v1/products/{product2.id}", headers=headers_admin)
    assert product1_response.json()["stock_quantity"] == initial_stock1 - 1
    assert product2_response.json()["stock_quantity"] == initial_stock2 - 2


@pytest.mark.asyncio
async def test_create_order_insufficient_stock(client: AsyncClient, test_users, test_deceased, test_products):
    headers = await get_auth_header(client, "family1")
    product = test_products[0]

    response = await client.post(
        "/api/v1/products/orders",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "items": [
                {"product_id": product.id, "quantity": 100}
            ]
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_order_refunds_stock(client: AsyncClient, test_users, test_deceased, test_products):
    headers = await get_auth_header(client, "family1")
    product = test_products[0]
    initial_stock = product.stock_quantity

    create_response = await client.post(
        "/api/v1/products/orders",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "items": [
                {"product_id": product.id, "quantity": 2}
            ]
        }
    )
    order_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/products/orders/{order_id}/cancel",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"

    headers_admin = await get_auth_header(client, "finance")
    product_response = await client.get(f"/api/v1/products/{product.id}", headers=headers_admin)
    assert product_response.json()["stock_quantity"] == initial_stock


@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient, test_users, test_deceased, test_products):
    headers = await get_auth_header(client, "family1")
    product = test_products[0]

    await client.post(
        "/api/v1/products/orders",
        headers=headers,
        json={
            "deceased_id": test_deceased.id,
            "items": [
                {"product_id": product.id, "quantity": 1}
            ]
        }
    )

    response = await client.get("/api/v1/products/orders", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_confirm_and_deliver_order(client: AsyncClient, test_users, test_deceased, test_products):
    headers_family = await get_auth_header(client, "family1")
    headers_finance = await get_auth_header(client, "finance")
    product = test_products[0]

    create_response = await client.post(
        "/api/v1/products/orders",
        headers=headers_family,
        json={
            "deceased_id": test_deceased.id,
            "items": [
                {"product_id": product.id, "quantity": 1}
            ]
        }
    )
    order_id = create_response.json()["id"]

    confirm_response = await client.post(
        f"/api/v1/products/orders/{order_id}/confirm",
        headers=headers_finance
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"

    deliver_response = await client.post(
        f"/api/v1/products/orders/{order_id}/deliver",
        headers=headers_finance
    )
    assert deliver_response.status_code == 200
    assert deliver_response.json()["status"] == "delivered"
