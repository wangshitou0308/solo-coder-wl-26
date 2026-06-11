from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.farewell import (
    FarewellHall,
    FarewellBooking,
    FarewellService,
    BookingStatus,
    HallLevel,
)
from app.schemas.farewell import (
    FarewellHallCreate,
    FarewellHallUpdate,
    FarewellBookingCreate,
    FarewellBookingUpdate,
    FarewellServiceCreate,
    TimeSlotCheck,
)
from app.services.deceased_service import get_deceased_by_id


async def get_hall_by_id(db: AsyncSession, hall_id: int):
    result = await db.execute(select(FarewellHall).where(FarewellHall.id == hall_id))
    hall = result.scalar_one_or_none()
    if not hall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告别厅不存在"
        )
    return hall


async def create_hall(db: AsyncSession, hall_in: FarewellHallCreate):
    existing = await db.execute(
        select(FarewellHall).where(FarewellHall.name == hall_in.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该告别厅名称已存在"
        )

    hall = FarewellHall(**hall_in.model_dump())
    db.add(hall)
    await db.commit()
    await db.refresh(hall)
    return hall


async def update_hall(db: AsyncSession, hall_id: int, hall_in: FarewellHallUpdate):
    hall = await get_hall_by_id(db, hall_id)
    update_data = hall_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hall, field, value)
    await db.commit()
    await db.refresh(hall)
    return hall


async def list_halls(
    db: AsyncSession,
    level: HallLevel | None = None,
    is_active: bool | None = None,
    min_capacity: int | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(FarewellHall)
    if level:
        query = query.where(FarewellHall.level == level)
    if is_active is not None:
        query = query.where(FarewellHall.is_active == is_active)
    if min_capacity:
        query = query.where(FarewellHall.capacity >= min_capacity)
    query = query.offset(skip).limit(limit).order_by(FarewellHall.level, FarewellHall.name)
    result = await db.execute(query)
    return result.scalars().all()


async def check_time_slot_conflict(
    db: AsyncSession,
    check: TimeSlotCheck
):
    query = select(FarewellBooking).where(
        FarewellBooking.hall_id == check.hall_id,
        FarewellBooking.status.notin_([BookingStatus.CANCELLED]),
        or_(
            and_(
                FarewellBooking.start_time < check.end_time,
                FarewellBooking.end_time > check.start_time
            )
        )
    )

    if check.exclude_booking_id:
        query = query.where(FarewellBooking.id != check.exclude_booking_id)

    result = await db.execute(query)
    conflicting = result.scalar_one_or_none()

    if conflicting:
        return {
            "has_conflict": True,
            "conflicting_booking": conflicting,
            "message": f"该时段与ID为{conflicting.id}的预约冲突"
        }
    return {
        "has_conflict": False,
        "conflicting_booking": None,
        "message": "该时段可用"
    }


async def get_booking_by_id(db: AsyncSession, booking_id: int):
    result = await db.execute(
        select(FarewellBooking)
        .options(
            joinedload(FarewellBooking.deceased),
            joinedload(FarewellBooking.hall),
            joinedload(FarewellBooking.services),
        )
        .where(FarewellBooking.id == booking_id)
    )
    booking = result.unique().scalar_one_or_none()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告别预约不存在"
        )
    return booking


async def calculate_booking_amount(
    db: AsyncSession,
    booking_in: FarewellBookingCreate
):
    hall = await get_hall_by_id(db, booking_in.hall_id)
    duration = booking_in.end_time - booking_in.start_time
    hours = duration.total_seconds() / 3600
    total_amount = float(hall.hourly_rate) * hours

    for service in booking_in.services:
        total_amount += service.unit_price * service.quantity

    if booking_in.require_photographer:
        total_amount += 500
    if booking_in.require_mc:
        total_amount += 800
    if booking_in.require_eulogy:
        total_amount += 300

    return total_amount


async def create_booking(
    db: AsyncSession,
    booking_in: FarewellBookingCreate,
    created_by: int
):
    deceased = await get_deceased_by_id(db, booking_in.deceased_id)
    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法创建告别预约"
        )

    hall = await get_hall_by_id(db, booking_in.hall_id)
    if not hall.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该告别厅已停用"
        )

    conflict = await check_time_slot_conflict(
        db,
        TimeSlotCheck(
            hall_id=booking_in.hall_id,
            start_time=booking_in.start_time,
            end_time=booking_in.end_time
        )
    )
    if conflict["has_conflict"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=conflict["message"]
        )

    existing_booking = await db.execute(
        select(FarewellBooking).where(
            FarewellBooking.deceased_id == booking_in.deceased_id,
            FarewellBooking.status != BookingStatus.CANCELLED
        )
    )
    if existing_booking.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者已有有效的告别预约"
        )

    total_amount = await calculate_booking_amount(db, booking_in)

    booking = FarewellBooking(
        **booking_in.model_dump(exclude={"services"}),
        created_by=created_by,
        status=BookingStatus.PENDING,
        total_amount=total_amount
    )
    db.add(booking)
    await db.flush()

    for service_in in booking_in.services:
        service = FarewellService(
            booking_id=booking.id,
            **service_in.model_dump(),
            subtotal=service_in.unit_price * service_in.quantity
        )
        db.add(service)

    await db.commit()
    await db.refresh(booking)
    return await get_booking_by_id(db, booking.id)


async def update_booking(
    db: AsyncSession,
    booking_id: int,
    booking_in: FarewellBookingUpdate
):
    booking = await get_booking_by_id(db, booking_id)

    if booking.deceased and booking.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改告别预约"
        )

    hall_id = booking_in.hall_id or booking.hall_id
    start_time = booking_in.start_time or booking.start_time
    end_time = booking_in.end_time or booking.end_time

    if booking_in.start_time or booking_in.end_time or booking_in.hall_id:
        conflict = await check_time_slot_conflict(
            db,
            TimeSlotCheck(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
                exclude_booking_id=booking_id
            )
        )
        if conflict["has_conflict"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=conflict["message"]
            )

    update_data = booking_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(booking, field, value)

    await db.commit()
    await db.refresh(booking)
    return await get_booking_by_id(db, booking_id)


async def list_bookings(
    db: AsyncSession,
    hall_id: int | None = None,
    status: BookingStatus | None = None,
    deceased_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = (
        select(FarewellBooking)
        .options(
            joinedload(FarewellBooking.deceased),
            joinedload(FarewellBooking.hall),
            joinedload(FarewellBooking.services),
        )
    )

    if hall_id:
        query = query.where(FarewellBooking.hall_id == hall_id)
    if status:
        query = query.where(FarewellBooking.status == status)
    if deceased_id:
        query = query.where(FarewellBooking.deceased_id == deceased_id)
    if start_date:
        query = query.where(func.date(FarewellBooking.start_time) >= start_date)
    if end_date:
        query = query.where(func.date(FarewellBooking.start_time) <= end_date)

    query = query.offset(skip).limit(limit).order_by(FarewellBooking.start_time)
    result = await db.execute(query)
    return result.unique().scalars().all()


async def cancel_booking(db: AsyncSession, booking_id: int):
    booking = await get_booking_by_id(db, booking_id)

    if booking.deceased and booking.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法取消预约"
        )

    if booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该预约已完成或已取消"
        )

    booking.status = BookingStatus.CANCELLED
    await db.commit()
    await db.refresh(booking)
    return await get_booking_by_id(db, booking_id)
