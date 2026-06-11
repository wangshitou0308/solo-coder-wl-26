from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.billing import (
    Bill,
    FeeItem,
    Payment,
    BillStatus,
    FeeType,
    PaymentMethod,
)
from app.schemas.billing import (
    BillCreate,
    BillUpdate,
    FeeItemCreate,
    PaymentReceipt,
)
from app.services.deceased_service import get_deceased_by_id


async def get_bill_by_id(db: AsyncSession, bill_id: int):
    result = await db.execute(
        select(Bill)
        .options(
            joinedload(Bill.deceased),
            joinedload(Bill.fee_items),
            joinedload(Bill.payments),
        )
        .where(Bill.id == bill_id)
    )
    bill = result.unique().scalar_one_or_none()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账单不存在"
        )
    return bill


async def generate_bill_no(db: AsyncSession):
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count(Bill.id))
        .where(func.date(Bill.created_at) == datetime.utcnow().date())
    )
    count = result.scalar() or 0
    return f"BILL{today}{count + 1:04d}"


async def calculate_total_amount(db: AsyncSession, bill_id: int):
    result = await db.execute(
        select(func.sum(FeeItem.subtotal))
        .where(FeeItem.bill_id == bill_id)
    )
    return result.scalar() or 0


async def create_bill(db: AsyncSession, bill_in: BillCreate):
    deceased = await get_deceased_by_id(db, bill_in.deceased_id)

    existing = await db.execute(
        select(Bill).where(
            Bill.deceased_id == bill_in.deceased_id,
            Bill.status != BillStatus.CANCELLED
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者已有未取消的账单"
        )

    bill_no = await generate_bill_no(db)
    bill = Bill(
        bill_no=bill_no,
        deceased_id=bill_in.deceased_id,
        remark=bill_in.remark,
        status=BillStatus.UNPAID
    )
    db.add(bill)
    await db.flush()

    total_amount = Decimal(0)
    for item_in in bill_in.fee_items:
        subtotal = Decimal(str(item_in.unit_price)) * Decimal(str(item_in.quantity))
        fee_item = FeeItem(
            bill_id=bill.id,
            **item_in.model_dump(),
            subtotal=subtotal
        )
        db.add(fee_item)
        total_amount += subtotal

    bill.total_amount = total_amount
    await db.commit()
    await db.refresh(bill)
    return await get_bill_by_id(db, bill.id)


async def update_bill(db: AsyncSession, bill_id: int, bill_in: BillUpdate):
    bill = await get_bill_by_id(db, bill_id)

    if bill.deceased and bill.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改账单"
        )

    update_data = bill_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bill, field, value)

    await db.commit()
    await db.refresh(bill)
    return bill


async def add_fee_items(
    db: AsyncSession,
    bill_id: int,
    items: list[FeeItemCreate]
):
    bill = await get_bill_by_id(db, bill_id)

    if bill.deceased and bill.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法添加费用项"
        )

    if bill.status == BillStatus.FULLY_PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账单已全额结清，无法添加费用项"
        )

    for item_in in items:
        subtotal = Decimal(str(item_in.unit_price)) * Decimal(str(item_in.quantity))
        fee_item = FeeItem(
            bill_id=bill.id,
            **item_in.model_dump(),
            subtotal=subtotal
        )
        db.add(fee_item)
        bill.total_amount += subtotal

    if bill.paid_amount >= bill.total_amount:
        bill.status = BillStatus.FULLY_PAID
    elif bill.paid_amount > 0:
        bill.status = BillStatus.PARTIAL_PAID
    else:
        bill.status = BillStatus.UNPAID

    await db.commit()
    await db.refresh(bill)
    return bill


async def process_payment(
    db: AsyncSession,
    payment_in: PaymentReceipt,
    collector_id: int
):
    bill = await get_bill_by_id(db, payment_in.bill_id)

    if bill.deceased and bill.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法收款"
        )

    if bill.status == BillStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账单已取消，无法收款"
        )

    payment_amount = Decimal(str(payment_in.amount))
    remaining = bill.total_amount - bill.paid_amount
    if payment_amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"收款金额超过剩余未付金额，剩余：{remaining}"
        )

    payment = Payment(
        bill_id=payment_in.bill_id,
        amount=payment_amount,
        payment_method=payment_in.payment_method,
        collector_id=collector_id,
        fee_item_id=payment_in.fee_item_id,
        remark=payment_in.remark
    )
    db.add(payment)

    bill.paid_amount += payment_amount
    if bill.paid_amount >= bill.total_amount:
        bill.status = BillStatus.FULLY_PAID
    elif bill.paid_amount > 0:
        bill.status = BillStatus.PARTIAL_PAID

    await db.commit()
    await db.refresh(bill)
    await db.refresh(payment)
    return payment


async def list_bills(
    db: AsyncSession,
    deceased_id: int | None = None,
    status: BillStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100
):
    query = (
        select(Bill)
        .options(
            joinedload(Bill.deceased),
            joinedload(Bill.fee_items),
            joinedload(Bill.payments),
        )
    )

    if deceased_id:
        query = query.where(Bill.deceased_id == deceased_id)
    if status:
        query = query.where(Bill.status == status)
    if start_date:
        query = query.where(Bill.created_at >= start_date)
    if end_date:
        query = query.where(Bill.created_at <= end_date)

    query = query.offset(skip).limit(limit).order_by(Bill.created_at.desc())
    result = await db.execute(query)
    return result.unique().scalars().all()


async def auto_generate_bill(db: AsyncSession, deceased_id: int):
    from app.models.transport import TransportOrder, TransportStatus
    from app.models.farewell import FarewellBooking, BookingStatus
    from app.models.cremation import CremationQueue, CremationStatus
    from app.models.product import ProductOrder, ProductOrderStatus

    deceased = await get_deceased_by_id(db, deceased_id)

    existing = await db.execute(
        select(Bill).where(
            Bill.deceased_id == deceased_id,
            Bill.status != BillStatus.CANCELLED
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者已有未取消的账单"
        )

    bill_no = await generate_bill_no(db)
    bill = Bill(
        bill_no=bill_no,
        deceased_id=deceased_id,
        status=BillStatus.UNPAID
    )
    db.add(bill)
    await db.flush()

    fee_items = []

    transport_result = await db.execute(
        select(TransportOrder).where(
            TransportOrder.deceased_id == deceased_id,
            TransportOrder.status == TransportStatus.COMPLETED
        )
    )
    transport = transport_result.scalar_one_or_none()
    if transport:
        fee_items.append(FeeItem(
            bill_id=bill.id,
            fee_type=FeeType.TRANSPORT,
            item_name="遗体接运费",
            description=f"从{transport.pickup_address}接运",
            quantity=1,
            unit_price=Decimal("800"),
            subtotal=Decimal("800"),
            reference_id=transport.id,
            reference_type="transport"
        ))

    booking_result = await db.execute(
        select(FarewellBooking)
        .options(joinedload(FarewellBooking.hall))
        .where(
            FarewellBooking.deceased_id == deceased_id,
            FarewellBooking.status.notin_([BookingStatus.CANCELLED])
        )
    )
    booking = booking_result.scalar_one_or_none()
    if booking:
        duration = (booking.end_time - booking.start_time).total_seconds() / 3600
        hall_fee = Decimal(str(booking.hall.hourly_rate)) * Decimal(str(duration))
        fee_items.append(FeeItem(
            bill_id=bill.id,
            fee_type=FeeType.FAREWELL,
            item_name=f"告别厅使用费-{booking.hall.name}",
            description=f"{booking.start_time.strftime('%Y-%m-%d %H:%M')} 至 {booking.end_time.strftime('%Y-%m-%d %H:%M')}",
            quantity=1,
            unit_price=hall_fee,
            subtotal=hall_fee,
            reference_id=booking.id,
            reference_type="farewell"
        ))

        if booking.require_photographer:
            fee_items.append(FeeItem(
                bill_id=bill.id,
                fee_type=FeeType.SERVICE,
                item_name="摄像服务",
                quantity=1,
                unit_price=Decimal("500"),
                subtotal=Decimal("500"),
                reference_id=booking.id,
                reference_type="farewell"
            ))
        if booking.require_mc:
            fee_items.append(FeeItem(
                bill_id=bill.id,
                fee_type=FeeType.SERVICE,
                item_name="司仪服务",
                quantity=1,
                unit_price=Decimal("800"),
                subtotal=Decimal("800"),
                reference_id=booking.id,
                reference_type="farewell"
            ))
        if booking.require_eulogy:
            fee_items.append(FeeItem(
                bill_id=bill.id,
                fee_type=FeeType.SERVICE,
                item_name="悼词代写",
                quantity=1,
                unit_price=Decimal("300"),
                subtotal=Decimal("300"),
                reference_id=booking.id,
                reference_type="farewell"
            ))

    cremation_result = await db.execute(
        select(CremationQueue).where(
            CremationQueue.deceased_id == deceased_id,
            CremationQueue.status != CremationStatus.CANCELLED
        )
    )
    cremation = cremation_result.scalar_one_or_none()
    if cremation:
        fee_items.append(FeeItem(
            bill_id=bill.id,
            fee_type=FeeType.CREMATION,
            item_name="火化费",
            quantity=1,
            unit_price=Decimal(str(cremation.cremation_fee)),
            subtotal=Decimal(str(cremation.cremation_fee)),
            reference_id=cremation.id,
            reference_type="cremation"
        ))
        if cremation.is_urgent:
            fee_items.append(FeeItem(
                bill_id=bill.id,
                fee_type=FeeType.SERVICE,
                item_name="加急处理费",
                quantity=1,
                unit_price=Decimal("500"),
                subtotal=Decimal("500"),
                reference_id=cremation.id,
                reference_type="cremation"
            ))

    orders_result = await db.execute(
        select(ProductOrder)
        .options(joinedload(ProductOrder.items))
        .where(
            ProductOrder.deceased_id == deceased_id,
            ProductOrder.status.notin_([ProductOrderStatus.CANCELLED])
        )
    )
    orders = orders_result.scalars().all()
    for order in orders:
        for item in order.items:
            fee_items.append(FeeItem(
                bill_id=bill.id,
                fee_type=FeeType.PRODUCT,
                item_name=f"丧葬用品-{item.product.name if hasattr(item, 'product') else '商品'}",
                quantity=item.quantity,
                unit_price=Decimal(str(item.unit_price)),
                subtotal=Decimal(str(item.subtotal)),
                reference_id=order.id,
                reference_type="product_order"
            ))

    total_amount = Decimal(0)
    for item in fee_items:
        db.add(item)
        total_amount += item.subtotal

    bill.total_amount = total_amount
    await db.commit()
    await db.refresh(bill)
    return await get_bill_by_id(db, bill.id)


async def cancel_bill(db: AsyncSession, bill_id: int):
    bill = await get_bill_by_id(db, bill_id)

    if bill.deceased and bill.deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法取消账单"
        )

    if bill.paid_amount > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账单已有收款记录，无法取消，请先退款"
        )

    bill.status = BillStatus.CANCELLED
    await db.commit()
    await db.refresh(bill)
    return bill
