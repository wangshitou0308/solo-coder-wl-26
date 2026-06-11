from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class FeeType(str, PyEnum):
    TRANSPORT = "transport"
    FAREWELL = "farewell"
    CREMATION = "cremation"
    PRODUCT = "product"
    SERVICE = "service"
    OTHER = "other"


class PaymentMethod(str, PyEnum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    WECHAT = "wechat"
    ALIPAY = "alipay"
    CARD = "card"
    OTHER = "other"


class BillStatus(str, PyEnum):
    UNPAID = "unpaid"
    PARTIAL_PAID = "partial_paid"
    FULLY_PAID = "fully_paid"
    CANCELLED = "cancelled"


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    bill_no = Column(String(50), unique=True, index=True, nullable=False)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), default=0)
    paid_amount = Column(Numeric(10, 2), default=0)
    status = Column(SAEnum(BillStatus), default=BillStatus.UNPAID)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deceased = relationship("Deceased", back_populates="bills")
    fee_items = relationship("FeeItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")


class FeeItem(Base):
    __tablename__ = "fee_items"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    fee_type = Column(SAEnum(FeeType), nullable=False)
    item_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String(50), nullable=True)

    bill = relationship("Bill", back_populates="fee_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(SAEnum(PaymentMethod), nullable=False)
    collector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fee_item_id = Column(Integer, ForeignKey("fee_items.id"), nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bill = relationship("Bill", back_populates="payments")
    collector = relationship("User", back_populates="payments")
