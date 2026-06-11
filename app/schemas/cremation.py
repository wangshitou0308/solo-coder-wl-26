from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.cremation import CremationStatus


class CremationQueueBase(BaseModel):
    is_urgent: bool = False
    special_time_window: Optional[datetime] = None
    cremation_fee: float = 0
    remark: Optional[str] = None


class CremationQueueCreate(CremationQueueBase):
    deceased_id: int


class CremationQueueUpdate(BaseModel):
    operator_id: Optional[int] = None
    is_urgent: Optional[bool] = None
    scheduled_time: Optional[datetime] = None
    special_time_window: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[CremationStatus] = None
    cremation_fee: Optional[float] = None
    remark: Optional[str] = None


class AshesCollection(BaseModel):
    ashes_receiver: str = Field(..., max_length=100)
    receiver_id_card: str = Field(..., max_length=18)
    receiver_phone: str = Field(..., max_length=20)
    relation_to_deceased: str = Field(..., max_length=50)


class CremationQueueResponse(CremationQueueBase):
    id: int
    deceased_id: int
    operator_id: Optional[int] = None
    queue_position: Optional[int] = None
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: CremationStatus
    ashes_receiver: Optional[str] = None
    receiver_id_card: Optional[str] = None
    receiver_phone: Optional[str] = None
    collected_at: Optional[datetime] = None
    relation_to_deceased: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QueuePosition(BaseModel):
    position: int
    total_in_queue: int
    estimated_wait_minutes: int
    cremation_id: int
    deceased_name: str
