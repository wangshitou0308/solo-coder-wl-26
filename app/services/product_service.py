from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.product import (
    Product,
    ProductOrder,
    ProductOrderItem,
    ProductCategory,
    ProductOrderStatus,
)
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductOrderCreate,
    ProductOrderUpdate,
)
from app.services.deceased_service import get_deceased_by_id


async def get_product_by_id(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    return product


async def create_product(db: AsyncSession, product_in: ProductCreate):
    existing = await db.execute(
        select(Product).where(Product.name == product_in.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该商品名称已存在"
        )

    product = Product(**product_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product_id: int, product_in: ProductUpdate):
    product = await get_product_by_id(db, product_id)
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def list_products(
    db: AsyncSession,
    category: ProductCategory | None = None,
    is_active: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(Product)
    if category:
        query = query.where(Product.category == category)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    if min_price:
        query = query.where(Product.price >= min_price)
    if max_price:
        query = query.where(Product.price <= max_price)
    query = query.offset(skip).limit(limit).order_by(Product.category, Product.name)
    result = await db.execute(query)
    return result.scalars().all()


async def get_order_by_id(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(ProductOrder)
        .options(
            joinedload(ProductOrder.deceased),
            joinedload(ProductOrder.items).joinedload(ProductOrderItem.product),
        )
        .where(ProductOrder.id == order_id)
    )
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    return order


async def generate_order_no(db: AsyncSession):
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count(ProductOrder.id))
        .where(func.date(ProductOrder.created_at) == datetime.utcnow().date())
    )
    count = result.scalar() or 0
    return f"ORD{today}{count + 1:04d}"


async def create_order(
    db: AsyncSession,
    order_in: ProductOrderCreate,
    created_by: int
):
    deceased = await get_deceased_by_id(db, order_in.deceased_id)
    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法创建用品订单"
        )

    order_no = await generate_order_no(db)

    total_amount = Decimal(0)
    for item_in in order_in.items:
        product = await get_product_by_id(db, item_in.product_id)
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品{product.name}已下架"
            )
        if product.stock_quantity < item_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品{product.name}库存不足，现有库存：{product.stock_quantity}"
            )
        total_amount += Decimal(str(product.price)) * Decimal(str(item_in.quantity))

    order = ProductOrder(
        order_no=order_no,
        deceased_id=order_in.deceased_id,
        created_by=created_by,
        total_amount=total_amount,
        status=ProductOrderStatus.PENDING,
        remark=order_in.remark
    )
    db.add(order)
    await db.flush()

    for item_in in order_in.items:
        product = await get_product_by_id(db, item_in.product_id)
        product.stock_quantity -= item_in.quantity

        item = ProductOrderItem(
            order_id=order.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=Decimal(str(product.price)),
            subtotal=Decimal(str(product.price)) * Decimal(str(item_in.quantity))
        )
        db.add(item)

    await db.commit()
    await db.refresh(order)
    return await get_order_by_id(db, order.id)


async def update_order(
    db: AsyncSession,
    order_id: int,
    order_in: ProductOrderUpdate
):
    order = await get_order_by_id(db, order_id)

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改订单"
        )

    update_data = order_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)
    return await get_order_by_id(db, order_id)


async def list_orders(
    db: AsyncSession,
    deceased_id: int | None = None,
    status: ProductOrderStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = (
        select(ProductOrder)
        .options(
            joinedload(ProductOrder.deceased),
            joinedload(ProductOrder.items).joinedload(ProductOrderItem.product),
        )
    )

    if deceased_id:
        query = query.where(ProductOrder.deceased_id == deceased_id)
    if status:
        query = query.where(ProductOrder.status == status)
    if start_date:
        query = query.where(ProductOrder.created_at >= start_date)
    if end_date:
        query = query.where(ProductOrder.created_at <= end_date)

    query = query.offset(skip).limit(limit).order_by(ProductOrder.created_at.desc())
    result = await db.execute(query)
    return result.unique().scalars().all()


async def cancel_order(db: AsyncSession, order_id: int):
    order = await get_order_by_id(db, order_id)

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法取消订单"
        )

    if order.status in [ProductOrderStatus.DELIVERED, ProductOrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该订单已发货或已取消"
        )

    for item in order.items:
        product = await get_product_by_id(db, item.product_id)
        product.stock_quantity += item.quantity

    order.status = ProductOrderStatus.CANCELLED
    await db.commit()
    await db.refresh(order)
    return await get_order_by_id(db, order_id)


async def deliver_order(db: AsyncSession, order_id: int):
    order = await get_order_by_id(db, order_id)

    if order.status != ProductOrderStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已确认的订单可以发货"
        )

    order.status = ProductOrderStatus.DELIVERED
    await db.commit()
    await db.refresh(order)
    return await get_order_by_id(db, order_id)


async def confirm_order(db: AsyncSession, order_id: int):
    order = await get_order_by_id(db, order_id)

    if order.status != ProductOrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有待处理的订单可以确认"
        )

    order.status = ProductOrderStatus.CONFIRMED
    await db.commit()
    await db.refresh(order)
    return await get_order_by_id(db, order_id)
