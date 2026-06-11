from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.billing import FeeType, PaymentMethod, BillStatus


class FeeItemBase(BaseModel):
    fee_type: FeeType
    item_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    quantity: int = 1
    unit_price: float
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None


class FeeItemCreate(FeeItemBase):
    pass


class FeeItemResponse(FeeItemBase):
    id: int
    bill_id: int
    subtotal: float

    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    fee_item_id: Optional[int] = None
    remark: Optional[str] = None


class PaymentCreate(PaymentBase):
    bill_id: int


class PaymentResponse(PaymentBase):
    id: int
    bill_id: int
    collector_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BillBase(BaseModel):
    deceased_id: int
    remark: Optional[str] = None


class BillCreate(BillBase):
    fee_items: List[FeeItemCreate] = []


class BillUpdate(BaseModel):
    status: Optional[BillStatus] = None
    remark: Optional[str] = None


class AddFeeItem(BaseModel):
    fee_items: List[FeeItemCreate]


class BillResponse(BaseModel):
    id: int
    bill_no: str
    deceased_id: int
    total_amount: float
    paid_amount: float
    status: BillStatus
    remark: Optional[str] = None
    fee_items: List[FeeItemResponse] = []
    payments: List[PaymentResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentReceipt(BaseModel):
    bill_id: int
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    fee_item_id: Optional[int] = None
    remark: Optional[str] = None
