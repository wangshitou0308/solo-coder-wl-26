from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.core.database import Base


class TransportStatus(str, PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransportOrder(Base):
    __tablename__ = "transport_orders"

    id = Column(Integer, primary_key=True, index=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    pickup_address = Column(String(255), nullable=False)
    pickup_contact = Column(String(100), nullable=False)
    pickup_phone = Column(String(20), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    actual_pickup_time = Column(DateTime, nullable=True)
    actual_arrival_time = Column(DateTime, nullable=True)
    status = Column(SAEnum(TransportStatus), default=TransportStatus.PENDING)
    vehicle_number = Column(String(50), nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deceased = relationship("Deceased", back_populates="transport_order")
    driver = relationship(
        "User",
        foreign_keys=[driver_id],
        back_populates="transport_orders_as_driver"
    )
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="transport_orders_as_creator"
    )
