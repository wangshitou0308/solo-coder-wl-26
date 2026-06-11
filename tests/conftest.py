import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.core.roles import UserRole
from app.models.user import User
from app.models.farewell import FarewellHall, HallLevel
from app.models.product import Product, ProductCategory
from app.models.deceased import Deceased
from app.models.family_relation import FamilyRelation
from main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./test_funeral_home.db"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
    )

    if "sqlite" in TEST_DATABASE_URL:
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    yield engine
    engine.sync_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_app(db_session: AsyncSession) -> FastAPI:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    del app.dependency_overrides[get_db]


@pytest_asyncio.fixture(scope="function")
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_users(db_session: AsyncSession):
    users = []
    roles = [
        ("director", UserRole.DIRECTOR),
        ("finance", UserRole.FINANCE),
        ("hall_admin", UserRole.HALL_ADMIN),
        ("cremation_op", UserRole.CREMATION_OPERATOR),
        ("driver1", UserRole.DRIVER),
        ("family1", UserRole.FAMILY_MEMBER),
    ]

    for username, role in roles:
        user = User(
            username=username,
            full_name=f"测试{username}",
            email=f"{username}@test.com",
            phone=f"1380000000{len(users)+1}",
            hashed_password=get_password_hash("123456"),
            role=role
        )
        db_session.add(user)
        users.append(user)

    await db_session.commit()
    for user in users:
        await db_session.refresh(user)

    return {u.username: u for u in users}


@pytest_asyncio.fixture(scope="function")
async def test_halls(db_session: AsyncSession):
    halls = [
        FarewellHall(name="测试厅1", level=HallLevel.STANDARD, capacity=50, hourly_rate=500),
        FarewellHall(name="测试厅2", level=HallLevel.DELUXE, capacity=100, hourly_rate=1500),
    ]
    for hall in halls:
        db_session.add(hall)
    await db_session.commit()
    for hall in halls:
        await db_session.refresh(hall)
    return halls


@pytest_asyncio.fixture(scope="function")
async def test_products(db_session: AsyncSession):
    products = [
        Product(name="测试骨灰盒", category=ProductCategory.URN, price=5000, stock_quantity=10),
        Product(name="测试寿衣", category=ProductCategory.SHROUD, price=3000, stock_quantity=20),
        Product(name="测试花圈", category=ProductCategory.WREATH, price=500, stock_quantity=50),
    ]
    for product in products:
        db_session.add(product)
    await db_session.commit()
    for product in products:
        await db_session.refresh(product)
    return products


@pytest_asyncio.fixture(scope="function")
async def test_deceased(db_session: AsyncSession, test_users):
    family_user = test_users["family1"]

    deceased = Deceased(
        name="测试逝者",
        gender="男",
        birth_date=datetime(1950, 1, 1).date(),
        death_date=datetime.utcnow().date(),
        id_card="110101195001011234",
        address="测试地址",
        death_place="测试地点"
    )
    db_session.add(deceased)
    await db_session.flush()

    relation = FamilyRelation(
        deceased_id=deceased.id,
        user_id=family_user.id,
        relation="儿子",
        contact_phone=family_user.phone,
        is_primary=1
    )
    db_session.add(relation)
    await db_session.commit()
    await db_session.refresh(deceased)

    return deceased


async def get_auth_header(client: AsyncClient, username: str, password: str = "123456"):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
