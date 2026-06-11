from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker
from app.core.roles import UserRole
from app.models.user import User
from app.models.farewell import BookingStatus, HallLevel
from app.schemas.farewell import (
    FarewellHallCreate,
    FarewellHallUpdate,
    FarewellHallResponse,
    FarewellBookingCreate,
    FarewellBookingUpdate,
    FarewellBookingResponse,
    TimeSlotCheck,
    TimeSlotConflict,
)
from app.services.farewell_service import (
    create_hall,
    get_hall_by_id,
    update_hall,
    list_halls,
    create_booking,
    get_booking_by_id,
    update_booking,
    list_bookings,
    check_time_slot_conflict,
    cancel_booking,
)
from app.services.deceased_service import get_deceased_by_id

router = APIRouter(prefix="/farewell", tags=["告别仪式预约管理"])


@router.post(
    "/halls",
    response_model=FarewellHallResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def create_new_hall(
    hall_in: FarewellHallCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_hall(db, hall_in)


@router.get(
    "/halls",
    response_model=list[FarewellHallResponse]
)
async def get_halls(
    level: HallLevel | None = None,
    is_active: bool | None = None,
    min_capacity: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await list_halls(db, level, is_active, min_capacity, skip, limit)


@router.get(
    "/halls/{hall_id}",
    response_model=FarewellHallResponse
)
async def get_hall(
    hall_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await get_hall_by_id(db, hall_id)


@router.put(
    "/halls/{hall_id}",
    response_model=FarewellHallResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def update_hall_info(
    hall_id: int,
    hall_in: FarewellHallUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_hall(db, hall_id, hall_in)


@router.post(
    "/check-slot",
    response_model=TimeSlotConflict
)
async def check_booking_slot(
    check_in: TimeSlotCheck,
    db: AsyncSession = Depends(get_db)
):
    return await check_time_slot_conflict(db, check_in)


@router.post(
    "/bookings",
    response_model=FarewellBookingResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def create_new_booking(
    booking_in: FarewellBookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    deceased = await get_deceased_by_id(db, booking_in.deceased_id)
    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法创建告别预约"
        )
    return await create_booking(db, booking_in, current_user.id)


@router.get(
    "/bookings",
    response_model=list[FarewellBookingResponse]
)
async def get_bookings(
    hall_id: int | None = None,
    booking_status: BookingStatus | None = None,
    deceased_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.FAMILY_MEMBER and deceased_id:
        deceased = await get_deceased_by_id(db, deceased_id)
        user_ids = [rel.user_id for rel in deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该逝者的预约"
            )

    return await list_bookings(db, hall_id, booking_status, deceased_id, start_date, end_date, skip, limit)


@router.get(
    "/bookings/{booking_id}",
    response_model=FarewellBookingResponse
)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    booking = await get_booking_by_id(db, booking_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in booking.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该预约"
            )

    return booking


@router.put(
    "/bookings/{booking_id}",
    response_model=FarewellBookingResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def update_booking_info(
    booking_id: int,
    booking_in: FarewellBookingUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_booking(db, booking_id, booking_in)


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=FarewellBookingResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def cancel_booking_route(
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await cancel_booking(db, booking_id)
