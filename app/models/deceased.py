from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Deceased(Base):
    __tablename__ = "deceased"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=False)
    birth_date = Column(Date, nullable=True)
    death_date = Column(Date, nullable=False)
    death_cause = Column(String(255), nullable=True)
    id_card = Column(String(18), unique=True, index=True, nullable=False)
    nationality = Column(String(50), nullable=True)
    ethnicity = Column(String(50), nullable=True)
    address = Column(String(255), nullable=False)
    death_place = Column(String(255), nullable=False)
    remark = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_relations = relationship("FamilyRelation", back_populates="deceased")
    transport_order = relationship("TransportOrder", back_populates="deceased", uselist=False)
    farewell_booking = relationship("FarewellBooking", back_populates="deceased", uselist=False)
    cremation = relationship("CremationQueue", back_populates="deceased", uselist=False)
    product_orders = relationship("ProductOrder", back_populates="deceased")
    bills = relationship("Bill", back_populates="deceased")
