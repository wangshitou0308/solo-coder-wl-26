from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.roles import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transport_orders_as_driver = relationship(
        "TransportOrder",
        foreign_keys="TransportOrder.driver_id",
        back_populates="driver"
    )
    transport_orders_as_creator = relationship(
        "TransportOrder",
        foreign_keys="TransportOrder.created_by",
        back_populates="creator"
    )
    bookings = relationship("FarewellBooking", back_populates="created_by_user")
    cremations = relationship("CremationQueue", back_populates="operator")
    payments = relationship("Payment", back_populates="collector")
    family_relations = relationship(
        "FamilyRelation",
        back_populates="user",
        foreign_keys="FamilyRelation.user_id"
    )
