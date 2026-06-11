from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Boolean, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class HallLevel(str, PyEnum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    PREMIUM = "premium"


class BookingStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DecorationType(str, PyEnum):
    FLOWERS = "flowers"
    SILK_FLOWERS = "silk_flowers"
    CUSTOM = "custom"


class FarewellHall(Base):
    __tablename__ = "farewell_halls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    level = Column(SAEnum(HallLevel), nullable=False)
    capacity = Column(Integer, nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("FarewellBooking", back_populates="hall")


class FarewellBooking(Base):
    __tablename__ = "farewell_bookings"

    id = Column(Integer, primary_key=True, index=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    hall_id = Column(Integer, ForeignKey("farewell_halls.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    decoration_type = Column(SAEnum(DecorationType), nullable=True)
    decoration_description = Column(Text, nullable=True)
    require_photographer = Column(Boolean, default=False)
    require_mc = Column(Boolean, default=False)
    require_eulogy = Column(Boolean, default=False)
    eulogy_content = Column(Text, nullable=True)
    elegiac_couplet = Column(Text, nullable=True)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)
    total_amount = Column(Numeric(10, 2), default=0)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deceased = relationship("Deceased", back_populates="farewell_booking")
    hall = relationship("FarewellHall", back_populates="bookings")
    created_by_user = relationship("User", back_populates="bookings")
    services = relationship("FarewellService", back_populates="booking")


class FarewellService(Base):
    __tablename__ = "farewell_services"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("farewell_bookings.id"), nullable=False)
    service_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    booking = relationship("FarewellBooking", back_populates="services")
