import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, Base, engine
from app.core.security import get_password_hash
from app.core.roles import UserRole
from app.models.user import User
from app.models.farewell import FarewellHall, HallLevel
from app.models.product import Product, ProductCategory
from app.models.deceased import Deceased
from app.models.family_relation import FamilyRelation
from app.models.transport import TransportOrder, TransportStatus
from app.models.farewell import FarewellBooking, BookingStatus, DecorationType, FarewellService
from app.models.cremation import CremationQueue, CremationStatus
from app.models.product import ProductOrder, ProductOrderItem, ProductOrderStatus
from app.models.billing import Bill, BillStatus, FeeItem, FeeType, Payment, PaymentMethod


async def create_default_users(db: AsyncSession):
    users_data = [
        {
            "username": "director",
            "full_name": "张馆长",
            "email": "director@funeral.com",
            "phone": "13800000001",
            "password": "123456",
            "role": UserRole.DIRECTOR
        },
        {
            "username": "finance",
            "full_name": "李会计",
            "email": "finance@funeral.com",
            "phone": "13800000002",
            "password": "123456",
            "role": UserRole.FINANCE
        },
        {
            "username": "hall_admin",
            "full_name": "王管理员",
            "email": "hall_admin@funeral.com",
            "phone": "13800000003",
            "password": "123456",
            "role": UserRole.HALL_ADMIN
        },
        {
            "username": "cremation_op",
            "full_name": "赵火化师",
            "email": "cremation@funeral.com",
            "phone": "13800000004",
            "password": "123456",
            "role": UserRole.CREMATION_OPERATOR
        },
        {
            "username": "driver1",
            "full_name": "孙司机",
            "email": "driver1@funeral.com",
            "phone": "13800000005",
            "password": "123456",
            "role": UserRole.DRIVER
        },
        {
            "username": "driver2",
            "full_name": "周司机",
            "email": "driver2@funeral.com",
            "phone": "13800000006",
            "password": "123456",
            "role": UserRole.DRIVER
        },
        {
            "username": "family1",
            "full_name": "家属刘先生",
            "email": "family1@example.com",
            "phone": "13900000001",
            "password": "123456",
            "role": UserRole.FAMILY_MEMBER
        },
        {
            "username": "family2",
            "full_name": "家属陈女士",
            "email": "family2@example.com",
            "phone": "13900000002",
            "password": "123456",
            "role": UserRole.FAMILY_MEMBER
        },
    ]

    for user_data in users_data:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == user_data["username"]))
        if not result.scalar_one_or_none():
            user = User(
                username=user_data["username"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                phone=user_data["phone"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"]
            )
            db.add(user)

    await db.commit()


async def create_default_halls(db: AsyncSession):
    from sqlalchemy import select
    result = await db.execute(select(FarewellHall))
    if not result.scalars().all():
        halls_data = [
            {
                "name": "福泽厅",
                "level": HallLevel.STANDARD,
                "capacity": 50,
                "hourly_rate": 500,
                "description": "标准告别厅，适合小型追悼会"
            },
            {
                "name": "祥瑞厅",
                "level": HallLevel.STANDARD,
                "capacity": 80,
                "hourly_rate": 800,
                "description": "标准告别厅，中型追悼会"
            },
            {
                "name": "豪华厅A",
                "level": HallLevel.DELUXE,
                "capacity": 150,
                "hourly_rate": 1500,
                "description": "豪华告别厅，配备高级音响设备"
            },
            {
                "name": "豪华厅B",
                "level": HallLevel.DELUXE,
                "capacity": 200,
                "hourly_rate": 2000,
                "description": "豪华告别厅，独立休息区"
            },
            {
                "name": "至尊厅",
                "level": HallLevel.PREMIUM,
                "capacity": 300,
                "hourly_rate": 5000,
                "description": "VIP尊享告别厅，全套高端设施"
            },
        ]

        for hall_data in halls_data:
            hall = FarewellHall(**hall_data)
            db.add(hall)

        await db.commit()


async def create_default_products(db: AsyncSession):
    from sqlalchemy import select
    result = await db.execute(select(Product))
    if not result.scalars().all():
        products_data = [
            {"name": "红木骨灰盒", "category": ProductCategory.URN, "price": 8800, "stock_quantity": 20, "description": "高档红木材质，精雕细刻"},
            {"name": "黑檀骨灰盒", "category": ProductCategory.URN, "price": 5800, "stock_quantity": 30, "description": "黑檀木，稳重典雅"},
            {"name": "陶瓷骨灰盒", "category": ProductCategory.URN, "price": 1800, "stock_quantity": 50, "description": "青花瓷工艺，精美图案"},
            {"name": "玉石骨灰盒", "category": ProductCategory.URN, "price": 12800, "stock_quantity": 10, "description": "天然玉石，温润细腻"},
            {"name": "男款寿衣七件套", "category": ProductCategory.SHROUD, "price": 3800, "stock_quantity": 25, "description": "传统唐装样式，高档面料"},
            {"name": "女款寿衣七件套", "category": ProductCategory.SHROUD, "price": 3800, "stock_quantity": 25, "description": "绣花款式，庄重典雅"},
            {"name": "现代款寿衣", "category": ProductCategory.SHROUD, "price": 2800, "stock_quantity": 30, "description": "西装/连衣裙款式"},
            {"name": "高档花圈", "category": ProductCategory.WREATH, "price": 800, "stock_quantity": 100, "description": "鲜花制作，直径1.5米"},
            {"name": "中档花圈", "category": ProductCategory.WREATH, "price": 300, "stock_quantity": 200, "description": "绢花制作，直径1.2米"},
            {"name": "电子花圈", "category": ProductCategory.WREATH, "price": 150, "stock_quantity": 50, "description": "可重复使用，环保节能"},
            {"name": "真丝寿毯", "category": ProductCategory.BLANKET, "price": 1200, "stock_quantity": 40, "description": "真丝材质，绣龙凤图案"},
            {"name": "纯棉寿毯", "category": ProductCategory.BLANKET, "price": 300, "stock_quantity": 60, "description": "纯棉材质，柔软舒适"},
            {"name": "水晶纪念品", "category": ProductCategory.SOUVENIR, "price": 600, "stock_quantity": 30, "description": "水晶内雕照片"},
            {"name": "金属纪念章", "category": ProductCategory.SOUVENIR, "price": 200, "stock_quantity": 100, "description": "定制刻字"},
            {"name": "骨灰吊坠", "category": ProductCategory.SOUVENIR, "price": 800, "stock_quantity": 20, "description": "可装入少量骨灰，随身携带"},
        ]

        for product_data in products_data:
            product = Product(**product_data)
            db.add(product)

        await db.commit()


async def create_sample_data(db: AsyncSession):
    from sqlalchemy import select

    result = await db.execute(select(Deceased))
    if result.scalars().all():
        return

    result = await db.execute(select(User).where(User.username == "family1"))
    family_user1 = result.scalar_one()
    result = await db.execute(select(User).where(User.username == "family2"))
    family_user2 = result.scalar_one()
    result = await db.execute(select(User).where(User.username == "hall_admin"))
    hall_admin = result.scalar_one()
    result = await db.execute(select(User).where(User.username == "driver1"))
    driver1 = result.scalar_one()
    result = await db.execute(select(User).where(User.username == "driver2"))
    driver2 = result.scalar_one()
    result = await db.execute(select(User).where(User.username == "cremation_op"))
    cremation_op = result.scalar_one()

    result = await db.execute(select(FarewellHall).where(FarewellHall.name == "福泽厅"))
    hall1 = result.scalar_one()
    result = await db.execute(select(FarewellHall).where(FarewellHall.name == "豪华厅A"))
    hall2 = result.scalar_one()

    now = datetime.utcnow()

    deceased1 = Deceased(
        name="张三",
        gender="男",
        birth_date=datetime(1950, 1, 1).date(),
        death_date=now.date(),
        death_cause="心脏病",
        id_card="110101195001011234",
        nationality="中国",
        ethnicity="汉",
        address="北京市朝阳区建国路88号",
        death_place="北京协和医院",
        remark="生前喜欢音乐"
    )
    db.add(deceased1)
    await db.flush()

    rel1 = FamilyRelation(
        deceased_id=deceased1.id,
        user_id=family_user1.id,
        relation="儿子",
        contact_phone=family_user1.phone,
        contact_address="北京市朝阳区建国路88号",
        is_primary=1
    )
    db.add(rel1)

    deceased2 = Deceased(
        name="李四",
        gender="女",
        birth_date=datetime(1945, 5, 15).date(),
        death_date=now.date(),
        death_cause="自然死亡",
        id_card="110101194505155678",
        nationality="中国",
        ethnicity="汉",
        address="北京市海淀区中关村大街1号",
        death_place="家中",
        remark="喜爱园艺"
    )
    db.add(deceased2)
    await db.flush()

    rel2 = FamilyRelation(
        deceased_id=deceased2.id,
        user_id=family_user2.id,
        relation="女儿",
        contact_phone=family_user2.phone,
        contact_address="北京市海淀区中关村大街1号",
        is_primary=1
    )
    db.add(rel2)

    transport1 = TransportOrder(
        deceased_id=deceased1.id,
        driver_id=driver1.id,
        created_by=hall_admin.id,
        pickup_address="北京协和医院",
        pickup_contact="刘先生",
        pickup_phone=family_user1.phone,
        scheduled_time=now + timedelta(hours=2),
        status=TransportStatus.ASSIGNED,
        vehicle_number="京A·12345"
    )
    db.add(transport1)

    transport2 = TransportOrder(
        deceased_id=deceased2.id,
        driver_id=driver2.id,
        created_by=hall_admin.id,
        pickup_address="北京市海淀区中关村大街1号",
        pickup_contact="陈女士",
        pickup_phone=family_user2.phone,
        scheduled_time=now + timedelta(hours=4),
        status=TransportStatus.PENDING,
        vehicle_number="京A·67890"
    )
    db.add(transport2)

    booking1 = FarewellBooking(
        deceased_id=deceased1.id,
        hall_id=hall1.id,
        created_by=hall_admin.id,
        start_time=now + timedelta(days=1, hours=9),
        end_time=now + timedelta(days=1, hours=11),
        decoration_type=DecorationType.FLOWERS,
        decoration_description="白色百合花装饰",
        require_photographer=True,
        require_mc=True,
        require_eulogy=True,
        eulogy_content="尊敬的各位亲友，今天我们怀着沉痛的心情...",
        elegiac_couplet="难忘手泽，永忆天伦",
        status=BookingStatus.CONFIRMED,
        total_amount=2800
    )
    db.add(booking1)
    await db.flush()

    service1 = FarewellService(
        booking_id=booking1.id,
        service_name="鲜花布置",
        description="白色百合花篮2个",
        quantity=2,
        unit_price=300,
        subtotal=600
    )
    db.add(service1)

    booking2 = FarewellBooking(
        deceased_id=deceased2.id,
        hall_id=hall2.id,
        created_by=hall_admin.id,
        start_time=now + timedelta(days=2, hours=10),
        end_time=now + timedelta(days=2, hours=12),
        decoration_type=DecorationType.SILK_FLOWERS,
        decoration_description="绢花装饰，肃穆庄重",
        require_photographer=False,
        require_mc=True,
        require_eulogy=False,
        status=BookingStatus.PENDING,
        total_amount=4800
    )
    db.add(booking2)

    cremation1 = CremationQueue(
        deceased_id=deceased1.id,
        operator_id=cremation_op.id,
        queue_position=1,
        is_urgent=False,
        scheduled_time=now + timedelta(days=1, hours=14),
        status=CremationStatus.QUEUED,
        cremation_fee=1500
    )
    db.add(cremation1)

    cremation2 = CremationQueue(
        deceased_id=deceased2.id,
        operator_id=None,
        queue_position=2,
        is_urgent=False,
        scheduled_time=now + timedelta(days=2, hours=14),
        status=CremationStatus.QUEUED,
        cremation_fee=1500
    )
    db.add(cremation2)

    result = await db.execute(select(Product).where(Product.name == "黑檀骨灰盒"))
    product1 = result.scalar_one()
    result = await db.execute(select(Product).where(Product.name == "男款寿衣七件套"))
    product2 = result.scalar_one()
    result = await db.execute(select(Product).where(Product.name == "高档花圈"))
    product3 = result.scalar_one()

    order_no = f"ORD{now.strftime('%Y%m%d')}0001"
    product_order1 = ProductOrder(
        order_no=order_no,
        deceased_id=deceased1.id,
        created_by=family_user1.id,
        total_amount=5800 + 3800 + 800 * 2,
        status=ProductOrderStatus.CONFIRMED
    )
    db.add(product_order1)
    await db.flush()

    order_items = [
        ProductOrderItem(order_id=product_order1.id, product_id=product1.id, quantity=1, unit_price=product1.price, subtotal=product1.price),
        ProductOrderItem(order_id=product_order1.id, product_id=product2.id, quantity=1, unit_price=product2.price, subtotal=product2.price),
        ProductOrderItem(order_id=product_order1.id, product_id=product3.id, quantity=2, unit_price=product3.price, subtotal=product3.price * 2),
    ]
    for item in order_items:
        db.add(item)

    await db.commit()
    print("示例数据创建完成！")


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await create_default_users(session)
        await create_default_halls(session)
        await create_default_products(session)
        await create_sample_data(session)
        print("数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(init_database())
