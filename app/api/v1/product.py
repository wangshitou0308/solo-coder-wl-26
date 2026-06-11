from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker
from app.core.roles import UserRole
from app.models.user import User
from app.models.product import ProductCategory, ProductOrderStatus
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductOrderCreate,
    ProductOrderUpdate,
    ProductOrderResponse,
)
from app.services.product_service import (
    create_product,
    get_product_by_id,
    update_product,
    list_products,
    create_order,
    get_order_by_id,
    update_order,
    list_orders,
    cancel_order,
    deliver_order,
    confirm_order,
)

router = APIRouter(prefix="/products", tags=["丧葬用品管理"])


@router.post(
    "",
    response_model=ProductResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def create_new_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_product(db, product_in)


@router.get(
    "",
    response_model=list[ProductResponse]
)
async def get_products(
    category: ProductCategory | None = None,
    is_active: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await list_products(db, category, is_active, min_price, max_price, skip, limit)


@router.post(
    "/orders",
    response_model=ProductOrderResponse
)
async def create_new_order(
    order_in: ProductOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_order(db, order_in, current_user.id)


@router.get(
    "/orders",
    response_model=list[ProductOrderResponse]
)
async def get_orders(
    deceased_id: int | None = None,
    order_status: ProductOrderStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.FAMILY_MEMBER and deceased_id:
        from app.services.deceased_service import get_deceased_by_id
        deceased = await get_deceased_by_id(db, deceased_id)
        user_ids = [rel.user_id for rel in deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该逝者的订单"
            )

    return await list_orders(db, deceased_id, order_status, start_date, end_date, skip, limit)


@router.get(
    "/orders/{order_id}",
    response_model=ProductOrderResponse
)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order = await get_order_by_id(db, order_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in order.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该订单"
            )

    return order


@router.put(
    "/orders/{order_id}",
    response_model=ProductOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def update_order_info(
    order_id: int,
    order_in: ProductOrderUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_order(db, order_id, order_in)


@router.post(
    "/orders/{order_id}/confirm",
    response_model=ProductOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def confirm_order_route(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await confirm_order(db, order_id)


@router.post(
    "/orders/{order_id}/deliver",
    response_model=ProductOrderResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def deliver_order_route(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await deliver_order(db, order_id)


@router.post(
    "/orders/{order_id}/cancel",
    response_model=ProductOrderResponse
)
async def cancel_order_route(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order = await get_order_by_id(db, order_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in order.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权取消该订单"
            )

    return await cancel_order(db, order_id)


@router.get(
    "/{product_id}",
    response_model=ProductResponse
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await get_product_by_id(db, product_id)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(RoleChecker(UserRole.FINANCE))]
)
async def update_product_info(
    product_id: int,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_product(db, product_id, product_in)
