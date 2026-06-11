from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.models.farewell import HallLevel, BookingStatus, DecorationType


class FarewellHallBase(BaseModel):
    name: str = Field(..., max_length=100)
    level: HallLevel
    capacity: int
    hourly_rate: float
    description: Optional[str] = None
    is_active: bool = True


class FarewellHallCreate(FarewellHallBase):
    pass


class FarewellHallUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[HallLevel] = None
    capacity: Optional[int] = None
    hourly_rate: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FarewellHallResponse(FarewellHallBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FarewellServiceBase(BaseModel):
    service_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    quantity: int = 1
    unit_price: float


class FarewellServiceCreate(FarewellServiceBase):
    pass


class FarewellServiceResponse(FarewellServiceBase):
    id: int
    booking_id: int
    subtotal: float

    class Config:
        from_attributes = True


class FarewellBookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    decoration_type: Optional[DecorationType] = None
    decoration_description: Optional[str] = None
    require_photographer: bool = False
    require_mc: bool = False
    require_eulogy: bool = False
    eulogy_content: Optional[str] = None
    elegiac_couplet: Optional[str] = None
    remark: Optional[str] = None
    services: List[FarewellServiceCreate] = []

    @field_validator("end_time")
    def end_time_after_start(cls, v, values):
        if "start_time" in values.data and v <= values.data["start_time"]:
            raise ValueError("结束时间必须晚于开始时间")
        duration = v - values.data["start_time"]
        if duration < timedelta(minutes=30):
            raise ValueError("预约时长至少为30分钟")
        return v


class FarewellBookingCreate(FarewellBookingBase):
    deceased_id: int
    hall_id: int


class FarewellBookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hall_id: Optional[int] = None
    decoration_type: Optional[DecorationType] = None
    decoration_description: Optional[str] = None
    require_photographer: Optional[bool] = None
    require_mc: Optional[bool] = None
    require_eulogy: Optional[bool] = None
    eulogy_content: Optional[str] = None
    elegiac_couplet: Optional[str] = None
    status: Optional[BookingStatus] = None
    remark: Optional[str] = None


class FarewellBookingResponse(FarewellBookingBase):
    id: int
    deceased_id: int
    hall_id: int
    hall: Optional[FarewellHallResponse] = None
    created_by: int
    status: BookingStatus
    total_amount: float
    services: List[FarewellServiceResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimeSlotCheck(BaseModel):
    hall_id: int
    start_time: datetime
    end_time: datetime
    exclude_booking_id: Optional[int] = None


class TimeSlotConflict(BaseModel):
    has_conflict: bool
    conflicting_booking: Optional[FarewellBookingResponse] = None
    message: str
