from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deceased import Deceased
from app.models.transport import TransportOrder, TransportStatus
from app.models.farewell import FarewellHall, FarewellBooking, BookingStatus
from app.models.cremation import CremationQueue, CremationStatus
from app.schemas.dashboard import (
    DashboardResponse,
    DailyStats,
    HallOccupancy,
    CremationDashboard,
    CremationQueueInfo,
    TransportDashboard,
    TransportTask,
)


async def get_daily_stats(db: AsyncSession):
    today = datetime.utcnow().date()

    total_result = await db.execute(select(func.count(Deceased.id)))
    total_deceased = total_result.scalar() or 0

    new_result = await db.execute(
        select(func.count(Deceased.id))
        .where(func.date(Deceased.created_at) == today)
    )
    new_deceased = new_result.scalar() or 0

    in_house_result = await db.execute(
        select(func.count(Deceased.id))
        .join(CremationQueue, Deceased.id == CremationQueue.deceased_id)
        .where(
            Deceased.is_archived == False,
            CremationQueue.status.notin_([
                CremationStatus.ASHES_COLLECTED,
                CremationStatus.CANCELLED
            ])
        )
    )
    in_house_deceased = in_house_result.scalar() or 0

    archived_result = await db.execute(
        select(func.count(Deceased.id))
        .where(Deceased.is_archived == True)
    )
    archived_deceased = archived_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(CremationQueue.id))
        .where(
            func.date(CremationQueue.collected_at) == today,
            CremationQueue.status == CremationStatus.ASHES_COLLECTED
        )
    )
    completed_services = completed_result.scalar() or 0

    return DailyStats(
        date=today.strftime("%Y-%m-%d"),
        total_deceased=total_deceased,
        new_deceased=new_deceased,
        in_house_deceased=in_house_deceased,
        archived_deceased=archived_deceased,
        completed_services=completed_services
    )


async def get_hall_occupancy(db: AsyncSession):
    now = datetime.utcnow()
    today = now.date()

    halls = await db.execute(select(FarewellHall).where(FarewellHall.is_active == True))
    halls_list = halls.scalars().all()

    occupancy_list = []
    for hall in halls_list:
        current_booking_result = await db.execute(
            select(FarewellBooking)
            .where(
                FarewellBooking.hall_id == hall.id,
                FarewellBooking.start_time <= now,
                FarewellBooking.end_time > now,
                FarewellBooking.status.notin_([BookingStatus.CANCELLED])
            )
        )
        current_booking = current_booking_result.scalar_one_or_none()

        today_count_result = await db.execute(
            select(func.count(FarewellBooking.id))
            .where(
                FarewellBooking.hall_id == hall.id,
                func.date(FarewellBooking.start_time) == today,
                FarewellBooking.status.notin_([BookingStatus.CANCELLED])
            )
        )
        today_count = today_count_result.scalar() or 0

        next_available_result = await db.execute(
            select(FarewellBooking.end_time)
            .where(
                FarewellBooking.hall_id == hall.id,
                FarewellBooking.end_time > now,
                FarewellBooking.status.notin_([BookingStatus.CANCELLED])
            )
            .order_by(FarewellBooking.end_time.asc())
        )
        next_end = next_available_result.scalar()
        next_available = next_end if next_end and next_end > now else now

        occupancy = HallOccupancy(
            hall_id=hall.id,
            hall_name=hall.name,
            level=hall.level.value,
            capacity=hall.capacity,
            is_occupied=current_booking is not None,
            current_booking={
                "id": current_booking.id,
                "start_time": current_booking.start_time,
                "end_time": current_booking.end_time
            } if current_booking else None,
            today_bookings_count=today_count,
            next_available=next_available
        )
        occupancy_list.append(occupancy)

    return occupancy_list


async def get_cremation_dashboard(db: AsyncSession):
    today = datetime.utcnow().date()
    now = datetime.utcnow()

    queue_result = await db.execute(
        select(CremationQueue)
        .options(
            selectinload(CremationQueue.deceased),
            selectinload(CremationQueue.operator),
        )
        .where(
            CremationQueue.status.in_([
                CremationStatus.QUEUED,
                CremationStatus.IN_PROGRESS,
                CremationStatus.COMPLETED,
                CremationStatus.ASHES_READY,
            ])
        )
        .order_by(
            CremationQueue.is_urgent.desc(),
            CremationQueue.queue_position,
            CremationQueue.created_at
        )
    )
    queue_list = queue_result.unique().scalars().all()

    queue_info = []
    total_wait = 0
    in_progress_count = 0

    for idx, cremation in enumerate(queue_list):
        if cremation.status == CremationStatus.IN_PROGRESS:
            in_progress_count += 1

        estimated = None
        if cremation.queue_position and cremation.status == CremationStatus.QUEUED:
            wait_minutes = (cremation.queue_position - 1) * 60
            total_wait += wait_minutes
            estimated = now + timedelta(minutes=wait_minutes)

        queue_info.append(CremationQueueInfo(
            cremation_id=cremation.id,
            deceased_name=cremation.deceased.name if cremation.deceased else "未知",
            queue_position=cremation.queue_position or (idx + 1),
            status=cremation.status,
            is_urgent=cremation.is_urgent,
            estimated_time=estimated,
            operator=cremation.operator.full_name if cremation.operator else None
        ))

    completed_today_result = await db.execute(
        select(func.count(CremationQueue.id))
        .where(
            func.date(CremationQueue.end_time) == today,
            CremationQueue.status.in_([
                CremationStatus.COMPLETED,
                CremationStatus.ASHES_READY,
                CremationStatus.ASHES_COLLECTED
            ])
        )
    )
    completed_today = completed_today_result.scalar() or 0

    queued_count = len([q for q in queue_list if q.status == CremationStatus.QUEUED])
    avg_wait = int(total_wait / queued_count) if queued_count > 0 else 0

    return CremationDashboard(
        total_in_queue=len(queue_list),
        in_progress=in_progress_count,
        completed_today=completed_today,
        average_wait_minutes=avg_wait,
        queue=queue_info
    )


async def get_transport_dashboard(db: AsyncSession):
    today = datetime.utcnow().date()
    now = datetime.utcnow()

    pending_result = await db.execute(
        select(func.count(TransportOrder.id))
        .where(
            func.date(TransportOrder.scheduled_time) == today,
            TransportOrder.status == TransportStatus.PENDING
        )
    )
    pending = pending_result.scalar() or 0

    in_progress_result = await db.execute(
        select(func.count(TransportOrder.id))
        .where(
            func.date(TransportOrder.scheduled_time) == today,
            TransportOrder.status == TransportStatus.IN_PROGRESS
        )
    )
    in_progress = in_progress_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(TransportOrder.id))
        .where(
            func.date(TransportOrder.actual_arrival_time) == today,
            TransportOrder.status == TransportStatus.COMPLETED
        )
    )
    completed = completed_result.scalar() or 0

    tasks_result = await db.execute(
        select(TransportOrder)
        .options(
            selectinload(TransportOrder.deceased),
            selectinload(TransportOrder.driver),
        )
        .where(
            func.date(TransportOrder.scheduled_time) == today,
            TransportOrder.status.notin_([TransportStatus.CANCELLED])
        )
        .order_by(TransportOrder.scheduled_time)
    )
    tasks_list = tasks_result.unique().scalars().all()

    tasks = []
    for task in tasks_list:
        tasks.append(TransportTask(
            order_id=task.id,
            deceased_name=task.deceased.name if task.deceased else "未知",
            pickup_address=task.pickup_address,
            pickup_contact=task.pickup_contact,
            pickup_phone=task.pickup_phone,
            scheduled_time=task.scheduled_time,
            status=task.status,
            driver_name=task.driver.full_name if task.driver else None
        ))

    return TransportDashboard(
        pending_tasks=pending,
        in_progress_tasks=in_progress,
        completed_today=completed,
        tasks=tasks
    )


async def get_dashboard(db: AsyncSession):
    daily_stats = await get_daily_stats(db)
    hall_occupancy = await get_hall_occupancy(db)
    cremation = await get_cremation_dashboard(db)
    transport = await get_transport_dashboard(db)

    return DashboardResponse(
        daily_stats=daily_stats,
        hall_occupancy=hall_occupancy,
        cremation=cremation,
        transport=transport,
        generated_at=datetime.utcnow()
    )
