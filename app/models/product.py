from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProductCategory(str, PyEnum):
    URN = "urn"
    SHROUD = "shroud"
    WREATH = "wreath"
    BLANKET = "blanket"
    SOUVENIR = "souvenir"
    OTHER = "other"


class ProductOrderStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(SAEnum(ProductCategory), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = relationship("ProductOrderItem", back_populates="product")


class ProductOrder(Base):
    __tablename__ = "product_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), default=0)
    status = Column(SAEnum(ProductOrderStatus), default=ProductOrderStatus.PENDING)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deceased = relationship("Deceased", back_populates="product_orders")
    items = relationship("ProductOrderItem", back_populates="order", cascade="all, delete-orphan")


class ProductOrderItem(Base):
    __tablename__ = "product_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("product_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("ProductOrder", back_populates="items")
    product = relationship("Product", back_populates="order_items")
