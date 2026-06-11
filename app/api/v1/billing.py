from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker
from app.core.roles import UserRole
from app.models.user import User
from app.models.billing import BillStatus
from app.schemas.billing import (
    BillCreate,
    BillUpdate,
    BillResponse,
    AddFeeItem,
    PaymentReceipt,
    PaymentResponse,
)
from app.services.billing_service import (
    create_bill,
    get_bill_by_id,
    update_bill,
    list_bills,
    add_fee_items,
    process_payment,
    auto_generate_bill,
    cancel_bill,
)

router = APIRouter(prefix="/billing", tags=["费用结算管理"])


@router.post(
    "",
    response_model=BillResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def create_new_bill(
    bill_in: BillCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_bill(db, bill_in)


@router.post(
    "/auto-generate/{deceased_id}",
    response_model=BillResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def auto_generate_bill_route(
    deceased_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await auto_generate_bill(db, deceased_id)


@router.get(
    "",
    response_model=list[BillResponse],
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def get_bills(
    deceased_id: int | None = None,
    bill_status: BillStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await list_bills(db, deceased_id, bill_status, start_date, end_date, skip, limit)


@router.get(
    "/{bill_id}",
    response_model=BillResponse
)
async def get_bill(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    bill = await get_bill_by_id(db, bill_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in bill.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该账单"
            )

    return bill


@router.put(
    "/{bill_id}",
    response_model=BillResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def update_bill_info(
    bill_id: int,
    bill_in: BillUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_bill(db, bill_id, bill_in)


@router.post(
    "/{bill_id}/fee-items",
    response_model=BillResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def add_fee_items_route(
    bill_id: int,
    items_in: AddFeeItem,
    db: AsyncSession = Depends(get_db)
):
    return await add_fee_items(db, bill_id, items_in.fee_items)


@router.post(
    "/pay",
    response_model=PaymentResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def process_payment_route(
    payment_in: PaymentReceipt,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await process_payment(db, payment_in, current_user.id)


@router.post(
    "/{bill_id}/cancel",
    response_model=BillResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def cancel_bill_route(
    bill_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await cancel_bill(db, bill_id)
