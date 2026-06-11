from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.transport import TransportStatus
from app.schemas.deceased import DeceasedResponse


class TransportOrderBase(BaseModel):
    pickup_address: str = Field(..., max_length=255)
    pickup_contact: str = Field(..., max_length=100)
    pickup_phone: str = Field(..., max_length=20)
    scheduled_time: datetime
    vehicle_number: Optional[str] = None
    remark: Optional[str] = None


class TransportOrderCreate(TransportOrderBase):
    deceased_id: int


class TransportOrderUpdate(BaseModel):
    pickup_address: Optional[str] = None
    pickup_contact: Optional[str] = None
    pickup_phone: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    driver_id: Optional[int] = None
    vehicle_number: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[TransportStatus] = None
    actual_pickup_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None


class AssignDriver(BaseModel):
    driver_id: int
    vehicle_number: Optional[str] = None


class TransportStatusUpdate(BaseModel):
    status: TransportStatus
    actual_pickup_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None


class TransportOrderResponse(TransportOrderBase):
    id: int
    deceased_id: int
    deceased: Optional[DeceasedResponse] = None
    driver_id: Optional[int] = None
    created_by: int
    status: TransportStatus
    actual_pickup_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
