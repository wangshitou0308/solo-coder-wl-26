from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Boolean, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class CremationStatus(str, PyEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ASHES_READY = "ashes_ready"
    ASHES_COLLECTED = "ashes_collected"
    CANCELLED = "cancelled"


class CremationQueue(Base):
    __tablename__ = "cremation_queue"

    id = Column(Integer, primary_key=True, index=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    queue_position = Column(Integer, nullable=True)
    is_urgent = Column(Boolean, default=False)
    scheduled_time = Column(DateTime, nullable=True)
    special_time_window = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(SAEnum(CremationStatus), default=CremationStatus.QUEUED)
    ashes_receiver = Column(String(100), nullable=True)
    receiver_id_card = Column(String(18), nullable=True)
    receiver_phone = Column(String(20), nullable=True)
    collected_at = Column(DateTime, nullable=True)
    relation_to_deceased = Column(String(50), nullable=True)
    cremation_fee = Column(Numeric(10, 2), default=0)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deceased = relationship("Deceased", back_populates="cremation")
    operator = relationship("User", back_populates="cremations")
