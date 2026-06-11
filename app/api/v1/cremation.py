from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker
from app.core.roles import UserRole
from app.models.user import User
from app.models.cremation import CremationStatus
from app.schemas.cremation import (
    CremationQueueCreate,
    CremationQueueUpdate,
    CremationQueueResponse,
    AshesCollection,
    QueuePosition,
)
from app.services.cremation_service import (
    create_cremation,
    get_cremation_by_id,
    update_cremation,
    list_cremations,
    start_cremation,
    complete_cremation,
    mark_ashes_ready,
    collect_ashes,
    get_queue_position,
    cancel_cremation,
    auto_schedule_cremation,
)

router = APIRouter(prefix="/cremation", tags=["火化排期管理"])


@router.post(
    "",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def create_new_cremation(
    cremation_in: CremationQueueCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_cremation(db, cremation_in)


@router.post(
    "/auto-schedule/{deceased_id}",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def auto_schedule(
    deceased_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await auto_schedule_cremation(db, deceased_id)


@router.get(
    "",
    response_model=list[CremationQueueResponse]
)
async def get_cremations(
    cremation_status: CremationStatus | None = None,
    deceased_id: int | None = None,
    is_urgent: bool | None = None,
    date_filter: date | None = None,
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
                detail="您无权查看该逝者的火化信息"
            )

    return await list_cremations(db, cremation_status, deceased_id, is_urgent, date_filter, skip, limit)


@router.get(
    "/{cremation_id}",
    response_model=CremationQueueResponse
)
async def get_cremation(
    cremation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cremation = await get_cremation_by_id(db, cremation_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in cremation.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该火化信息"
            )

    return cremation


@router.get(
    "/{cremation_id}/position",
    response_model=QueuePosition
)
async def get_cremation_position(
    cremation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cremation = await get_cremation_by_id(db, cremation_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in cremation.deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该火化信息"
            )

    return await get_queue_position(db, cremation_id)


@router.put(
    "/{cremation_id}",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def update_cremation_info(
    cremation_id: int,
    cremation_in: CremationQueueUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_cremation(db, cremation_id, cremation_in)


@router.post(
    "/{cremation_id}/start",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def start_cremation_route(
    cremation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await start_cremation(db, cremation_id, current_user.id)


@router.post(
    "/{cremation_id}/complete",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def complete_cremation_route(
    cremation_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await complete_cremation(db, cremation_id)


@router.post(
    "/{cremation_id}/ashes-ready",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def mark_ashes_ready_route(
    cremation_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await mark_ashes_ready(db, cremation_id)


@router.post(
    "/{cremation_id}/collect-ashes",
    response_model=CremationQueueResponse
)
async def collect_ashes_route(
    cremation_id: int,
    collection_in: AshesCollection,
    db: AsyncSession = Depends(get_db)
):
    return await collect_ashes(db, cremation_id, collection_in)


@router.post(
    "/{cremation_id}/cancel",
    response_model=CremationQueueResponse,
    dependencies=[Depends(RoleChecker(UserRole.CREMATION_OPERATOR))]
)
async def cancel_cremation_route(
    cremation_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await cancel_cremation(db, cremation_id)
