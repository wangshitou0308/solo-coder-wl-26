from datetime import datetime, date
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.transport import TransportOrder, TransportStatus
from app.models.user import User
from app.models.deceased import Deceased
from app.core.roles import UserRole
from app.schemas.transport import (
    TransportOrderCreate,
    TransportOrderUpdate,
    AssignDriver,
    TransportStatusUpdate,
)
from app.services.deceased_service import get_deceased_by_id
from app.services.auth_service import get_user_by_id


async def get_transport_order_by_id(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(TransportOrder)
        .options(
            joinedload(TransportOrder.deceased),
            joinedload(TransportOrder.driver),
            joinedload(TransportOrder.creator),
        )
        .where(TransportOrder.id == order_id)
    )
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接运工单不存在"
        )
    return order


async def create_transport_order(
    db: AsyncSession,
    order_in: TransportOrderCreate,
    created_by: int
):
    deceased = await get_deceased_by_id(db, order_in.deceased_id)
    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法创建接运工单"
        )

    existing_order = await db.execute(
        select(TransportOrder).where(
            TransportOrder.deceased_id == order_in.deceased_id,
            TransportOrder.status != TransportStatus.CANCELLED
        )
    )
    if existing_order.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者已有有效的接运工单"
        )

    order = TransportOrder(
        **order_in.model_dump(),
        created_by=created_by,
        status=TransportStatus.PENDING
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return await get_transport_order_by_id(db, order.id)


async def update_transport_order(
    db: AsyncSession,
    order_id: int,
    order_in: TransportOrderUpdate
):
    order = await get_transport_order_by_id(db, order_id)

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改接运工单"
        )

    update_data = order_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)
    return order


async def assign_driver(
    db: AsyncSession,
    order_id: int,
    assign_in: AssignDriver
):
    order = await get_transport_order_by_id(db, order_id)

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法分配司机"
        )

    driver = await get_user_by_id(db, assign_in.driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定的司机不存在或不是司机角色"
        )

    order.driver_id = assign_in.driver_id
    order.vehicle_number = assign_in.vehicle_number
    order.status = TransportStatus.ASSIGNED
    await db.commit()
    await db.refresh(order)
    return order


async def update_transport_status(
    db: AsyncSession,
    order_id: int,
    status_in: TransportStatusUpdate,
    driver_id: int | None = None
):
    order = await get_transport_order_by_id(db, order_id)

    if driver_id and order.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该工单的指定司机，无法更新状态"
        )

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法更新状态"
        )

    order.status = status_in.status
    if status_in.actual_pickup_time:
        order.actual_pickup_time = status_in.actual_pickup_time
    if status_in.actual_arrival_time:
        order.actual_arrival_time = status_in.actual_arrival_time

    await db.commit()
    await db.refresh(order)
    return order


async def list_transport_orders(
    db: AsyncSession,
    status: TransportStatus | None = None,
    driver_id: int | None = None,
    scheduled_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_by_address: bool = False
):
    query = (
        select(TransportOrder)
        .options(
            joinedload(TransportOrder.deceased),
            joinedload(TransportOrder.driver),
        )
    )

    if status:
        query = query.where(TransportOrder.status == status)
    if driver_id:
        query = query.where(TransportOrder.driver_id == driver_id)
    if scheduled_date:
        query = query.where(
            func.date(TransportOrder.scheduled_time) == scheduled_date
        )

    if sort_by_address:
        query = query.order_by(TransportOrder.pickup_address)
    else:
        query = query.order_by(TransportOrder.scheduled_time)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.unique().scalars().all()


async def get_driver_today_tasks(
    db: AsyncSession,
    driver_id: int,
    sort_by_address: bool = True
):
    today = datetime.utcnow().date()
    return await list_transport_orders(
        db=db,
        driver_id=driver_id,
        scheduled_date=today,
        sort_by_address=sort_by_address
    )


async def cancel_transport_order(db: AsyncSession, order_id: int):
    order = await get_transport_order_by_id(db, order_id)

    if order.deceased and order.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法取消工单"
        )

    if order.status in [TransportStatus.COMPLETED, TransportStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该工单已完成或已取消，无法再次取消"
        )

    order.status = TransportStatus.CANCELLED
    await db.commit()
    await db.refresh(order)
    return order
