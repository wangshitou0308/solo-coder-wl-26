from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker, check_archived_deceased
from app.core.roles import UserRole
from app.models.user import User
from app.models.transport import TransportStatus
from app.schemas.transport import (
    TransportOrderCreate,
    TransportOrderUpdate,
    TransportOrderResponse,
    AssignDriver,
    TransportStatusUpdate,
)
from app.services.transport_service import (
    create_transport_order,
    get_transport_order_by_id,
    update_transport_order,
    list_transport_orders,
    assign_driver,
    update_transport_status,
    get_driver_today_tasks,
    cancel_transport_order,
)

router = APIRouter(prefix="/transport", tags=["遗体接运管理"])


@router.post(
    "",
    response_model=TransportOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def create_new_transport_order(
    order_in: TransportOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_archived_deceased(order_in.deceased_id, db)
    return await create_transport_order(db, order_in, current_user.id)


@router.get(
    "",
    response_model=list[TransportOrderResponse]
)
async def get_transport_orders(
    transport_status: TransportStatus | None = None,
    driver_id: int | None = None,
    scheduled_date: date | None = None,
    sort_by_address: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.DRIVER:
        driver_id = current_user.id

    return await list_transport_orders(
        db, transport_status, driver_id, scheduled_date, skip, limit, sort_by_address
    )


@router.get(
    "/my-tasks",
    response_model=list[TransportOrderResponse],
    dependencies=[Depends(RoleChecker(UserRole.DRIVER))]
)
async def get_my_today_tasks(
    sort_by_address: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_driver_today_tasks(db, current_user.id, sort_by_address)


@router.get(
    "/{order_id}",
    response_model=TransportOrderResponse
)
async def get_transport_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order = await get_transport_order_by_id(db, order_id)

    if current_user.role == UserRole.DRIVER and order.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权查看该接运工单"
        )
    if current_user.role == UserRole.FAMILY_MEMBER:
        family_user_ids = [rel.user_id for rel in order.deceased.family_relations]
        if current_user.id not in family_user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该接运工单"
            )

    return order


@router.put(
    "/{order_id}",
    response_model=TransportOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def update_transport_order_info(
    order_id: int,
    order_in: TransportOrderUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_transport_order(db, order_id, order_in)


@router.post(
    "/{order_id}/assign-driver",
    response_model=TransportOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def assign_driver_to_order(
    order_id: int,
    assign_in: AssignDriver,
    db: AsyncSession = Depends(get_db)
):
    return await assign_driver(db, order_id, assign_in)


@router.post(
    "/{order_id}/status",
    response_model=TransportOrderResponse
)
async def update_order_status(
    order_id: int,
    status_in: TransportStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    driver_id = current_user.id if current_user.role == UserRole.DRIVER else None
    return await update_transport_status(db, order_id, status_in, driver_id)


@router.post(
    "/{order_id}/cancel",
    response_model=TransportOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await cancel_transport_order(db, order_id)
