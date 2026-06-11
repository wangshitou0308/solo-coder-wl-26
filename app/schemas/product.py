from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.product import ProductCategory, ProductOrderStatus


class ProductBase(BaseModel):
    name: str = Field(..., max_length=200)
    category: ProductCategory
    description: Optional[str] = None
    price: float
    stock_quantity: int = 0
    min_stock: int = 0
    is_active: int = 1


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ProductCategory] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    min_stock: Optional[int] = None
    is_active: Optional[int] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductOrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)


class ProductOrderItemCreate(ProductOrderItemBase):
    pass


class ProductOrderItemResponse(ProductOrderItemBase):
    id: int
    order_id: int
    unit_price: float
    subtotal: float
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True


class ProductOrderBase(BaseModel):
    deceased_id: int
    remark: Optional[str] = None
    items: List[ProductOrderItemCreate]


class ProductOrderCreate(ProductOrderBase):
    pass


class ProductOrderUpdate(BaseModel):
    status: Optional[ProductOrderStatus] = None
    remark: Optional[str] = None


class ProductOrderResponse(BaseModel):
    id: int
    order_no: str
    deceased_id: int
    created_by: int
    total_amount: float
    status: ProductOrderStatus
    remark: Optional[str] = None
    items: List[ProductOrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
