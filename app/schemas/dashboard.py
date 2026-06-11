from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.models.farewell import BookingStatus
from app.models.cremation import CremationStatus
from app.models.transport import TransportStatus


class DailyStats(BaseModel):
    date: str
    total_deceased: int
    new_deceased: int
    in_house_deceased: int
    archived_deceased: int
    completed_services: int


class HallOccupancy(BaseModel):
    hall_id: int
    hall_name: str
    level: str
    capacity: int
    is_occupied: bool
    current_booking: Optional[dict] = None
    today_bookings_count: int
    next_available: Optional[datetime] = None


class CremationQueueInfo(BaseModel):
    cremation_id: int
    deceased_name: str
    queue_position: int
    status: CremationStatus
    is_urgent: bool
    estimated_time: Optional[datetime] = None
    operator: Optional[str] = None


class CremationDashboard(BaseModel):
    total_in_queue: int
    in_progress: int
    completed_today: int
    average_wait_minutes: int
    queue: List[CremationQueueInfo] = []


class TransportTask(BaseModel):
    order_id: int
    deceased_name: str
    pickup_address: str
    pickup_contact: str
    pickup_phone: str
    scheduled_time: datetime
    status: TransportStatus
    driver_name: Optional[str] = None


class TransportDashboard(BaseModel):
    pending_tasks: int
    in_progress_tasks: int
    completed_today: int
    tasks: List[TransportTask] = []


class DashboardResponse(BaseModel):
    daily_stats: DailyStats
    hall_occupancy: List[HallOccupancy]
    cremation: CremationDashboard
    transport: TransportDashboard
    generated_at: datetime
