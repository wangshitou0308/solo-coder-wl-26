from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.cremation import CremationQueue, CremationStatus
from app.models.farewell import FarewellBooking, BookingStatus
from app.models.transport import TransportOrder, TransportStatus
from app.schemas.cremation import (
    CremationQueueCreate,
    CremationQueueUpdate,
    AshesCollection,
)
from app.services.deceased_service import get_deceased_by_id


async def get_cremation_by_id(db: AsyncSession, cremation_id: int):
    result = await db.execute(
        select(CremationQueue)
        .options(
            joinedload(CremationQueue.deceased),
            joinedload(CremationQueue.operator),
        )
        .where(CremationQueue.id == cremation_id)
    )
    cremation = result.unique().scalar_one_or_none()
    if not cremation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="火化记录不存在"
        )
    return cremation


async def recalculate_queue_positions(db: AsyncSession):
    result = await db.execute(
        select(CremationQueue)
        .where(
            CremationQueue.status.in_([
                CremationStatus.QUEUED,
                CremationStatus.IN_PROGRESS
            ])
        )
        .order_by(
            CremationQueue.is_urgent.desc(),
            CremationQueue.created_at
        )
    )
    cremations = result.scalars().all()

    for idx, cremation in enumerate(cremations, 1):
        cremation.queue_position = idx

    await db.commit()


async def get_earliest_available_time(db: AsyncSession):
    result = await db.execute(
        select(func.max(CremationQueue.end_time))
        .where(CremationQueue.status.in_([
            CremationStatus.QUEUED,
            CremationStatus.IN_PROGRESS
        ]))
    )
    max_end = result.scalar()

    if max_end:
        return max_end + timedelta(minutes=30)

    transport_result = await db.execute(
        select(func.max(TransportOrder.actual_arrival_time))
        .where(TransportOrder.status == TransportStatus.COMPLETED)
    )
    latest_arrival = transport_result.scalar()

    if latest_arrival and latest_arrival > datetime.utcnow():
        return latest_arrival + timedelta(minutes=30)

    return datetime.utcnow() + timedelta(minutes=30)


async def create_cremation(
    db: AsyncSession,
    cremation_in: CremationQueueCreate
):
    deceased = await get_deceased_by_id(db, cremation_in.deceased_id)
    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法安排火化"
        )

    existing = await db.execute(
        select(CremationQueue).where(
            CremationQueue.deceased_id == cremation_in.deceased_id,
            CremationQueue.status != CremationStatus.CANCELLED
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者已在火化队列中"
        )

    scheduled_time = cremation_in.special_time_window or await get_earliest_available_time(db)

    cremation = CremationQueue(
        **cremation_in.model_dump(),
        scheduled_time=scheduled_time,
        status=CremationStatus.QUEUED
    )
    db.add(cremation)
    await db.flush()

    await recalculate_queue_positions(db)
    await db.refresh(cremation)
    return await get_cremation_by_id(db, cremation.id)


async def auto_schedule_cremation(db: AsyncSession, deceased_id: int):
    existing_farewell = await db.execute(
        select(FarewellBooking)
        .where(
            FarewellBooking.deceased_id == deceased_id,
            FarewellBooking.status.notin_([BookingStatus.CANCELLED])
        )
        .order_by(FarewellBooking.end_time.desc())
    )
    farewell = existing_farewell.scalar_one_or_none()

    existing_transport = await db.execute(
        select(TransportOrder)
        .where(
            TransportOrder.deceased_id == deceased_id,
            TransportOrder.status == TransportStatus.COMPLETED
        )
        .order_by(TransportOrder.actual_arrival_time.desc())
    )
    transport = existing_transport.scalar_one_or_none()

    scheduled_time = datetime.utcnow() + timedelta(minutes=60)
    if farewell:
        scheduled_time = farewell.end_time + timedelta(minutes=30)
    elif transport and transport.actual_arrival_time:
        scheduled_time = transport.actual_arrival_time + timedelta(minutes=60)

    cremation_in = CremationQueueCreate(
        deceased_id=deceased_id,
        cremation_fee=1500.0
    )

    cremation = CremationQueue(
        **cremation_in.model_dump(),
        scheduled_time=scheduled_time,
        status=CremationStatus.QUEUED
    )
    db.add(cremation)
    await db.flush()
    await recalculate_queue_positions(db)
    await db.commit()
    await db.refresh(cremation)
    return cremation


async def update_cremation(
    db: AsyncSession,
    cremation_id: int,
    cremation_in: CremationQueueUpdate
):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.deceased and cremation.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改火化记录"
        )

    old_status = cremation.status
    update_data = cremation_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cremation, field, value)

    if "status" in update_data or "is_urgent" in update_data:
        await recalculate_queue_positions(db)

    await db.commit()
    await db.refresh(cremation)
    return cremation


async def start_cremation(db: AsyncSession, cremation_id: int, operator_id: int):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.status != CremationStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有排队中的火化可以开始"
        )

    cremation.status = CremationStatus.IN_PROGRESS
    cremation.start_time = datetime.utcnow()
    cremation.operator_id = operator_id

    await recalculate_queue_positions(db)
    await db.commit()
    await db.refresh(cremation)
    return cremation


async def complete_cremation(db: AsyncSession, cremation_id: int):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.status != CremationStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有进行中的火化可以完成"
        )

    cremation.status = CremationStatus.COMPLETED
    cremation.end_time = datetime.utcnow()

    await recalculate_queue_positions(db)
    await db.commit()
    await db.refresh(cremation)
    return cremation


async def mark_ashes_ready(db: AsyncSession, cremation_id: int):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.status != CremationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已完成火化的可以标记骨灰就绪"
        )

    cremation.status = CremationStatus.ASHES_READY
    await db.commit()
    await db.refresh(cremation)
    return cremation


async def collect_ashes(
    db: AsyncSession,
    cremation_id: int,
    collection_in: AshesCollection
):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.status != CremationStatus.ASHES_READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有骨灰就绪状态的可以领取"
        )

    cremation.status = CremationStatus.ASHES_COLLECTED
    cremation.ashes_receiver = collection_in.ashes_receiver
    cremation.receiver_id_card = collection_in.receiver_id_card
    cremation.receiver_phone = collection_in.receiver_phone
    cremation.relation_to_deceased = collection_in.relation_to_deceased
    cremation.collected_at = datetime.utcnow()

    await db.commit()
    await db.refresh(cremation)
    return cremation


async def list_cremations(
    db: AsyncSession,
    status: CremationStatus | None = None,
    deceased_id: int | None = None,
    is_urgent: bool | None = None,
    date: date | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = (
        select(CremationQueue)
        .options(
            joinedload(CremationQueue.deceased),
            joinedload(CremationQueue.operator),
        )
    )

    if status:
        query = query.where(CremationQueue.status == status)
    if deceased_id:
        query = query.where(CremationQueue.deceased_id == deceased_id)
    if is_urgent is not None:
        query = query.where(CremationQueue.is_urgent == is_urgent)
    if date:
        query = query.where(func.date(CremationQueue.created_at) == date)

    query = query.order_by(
        CremationQueue.is_urgent.desc(),
        CremationQueue.queue_position,
        CremationQueue.created_at
    )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.unique().scalars().all()


async def get_queue_position(db: AsyncSession, cremation_id: int):
    cremation = await get_cremation_by_id(db, cremation_id)

    result = await db.execute(
        select(func.count(CremationQueue.id))
        .where(
            CremationQueue.status.in_([
                CremationStatus.QUEUED,
                CremationStatus.IN_PROGRESS
            ])
        )
    )
    total = result.scalar() or 0

    estimated_wait = 0
    if cremation.queue_position:
        estimated_wait = (cremation.queue_position - 1) * 60

    return {
        "position": cremation.queue_position or total,
        "total_in_queue": total,
        "estimated_wait_minutes": estimated_wait,
        "cremation_id": cremation.id,
        "deceased_name": cremation.deceased.name if cremation.deceased else "未知"
    }


async def cancel_cremation(db: AsyncSession, cremation_id: int):
    cremation = await get_cremation_by_id(db, cremation_id)

    if cremation.deceased and cremation.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法取消火化"
        )

    if cremation.status in [
        CremationStatus.IN_PROGRESS,
        CremationStatus.COMPLETED,
        CremationStatus.ASHES_READY,
        CremationStatus.ASHES_COLLECTED,
        CremationStatus.CANCELLED
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该火化已进行或已完成，无法取消"
        )

    cremation.status = CremationStatus.CANCELLED
    cremation.queue_position = None
    await recalculate_queue_positions(db)
    await db.commit()
    await db.refresh(cremation)
    return cremation
