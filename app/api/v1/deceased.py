from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker, check_archived_deceased
from app.core.roles import UserRole
from app.models.user import User
from app.schemas.deceased import (
    DeceasedCreate,
    DeceasedUpdate,
    DeceasedResponse,
    DeceasedArchive,
)
from app.services.deceased_service import (
    create_deceased,
    get_deceased_by_id,
    update_deceased,
    list_deceased,
    archive_deceased,
)

router = APIRouter(prefix="/deceased", tags=["逝者档案管理"])


@router.post(
    "",
    response_model=DeceasedResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def create_new_deceased(
    deceased_in: DeceasedCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_deceased(db, deceased_in, current_user.id)


@router.get(
    "",
    response_model=list[DeceasedResponse],
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def get_deceased_list(
    include_archived: bool = False,
    name: str | None = None,
    id_card: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await list_deceased(db, skip, limit, include_archived, name, id_card)


@router.get(
    "/{deceased_id}",
    response_model=DeceasedResponse
)
async def get_deceased(
    deceased_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    deceased = await get_deceased_by_id(db, deceased_id)

    if current_user.role == UserRole.FAMILY_MEMBER:
        user_ids = [rel.user_id for rel in deceased.family_relations]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看该逝者档案"
            )

    return deceased


@router.put(
    "/{deceased_id}",
    response_model=DeceasedResponse,
    dependencies=[Depends(RoleChecker(UserRole.HALL_ADMIN))]
)
async def update_deceased_info(
    deceased_id: int,
    deceased_in: DeceasedUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_archived_deceased)
):
    return await update_deceased(db, deceased_id, deceased_in)


@router.post(
    "/{deceased_id}/archive",
    response_model=DeceasedResponse,
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def archive_deceased_record(
    deceased_id: int,
    archive_in: DeceasedArchive,
    db: AsyncSession = Depends(get_db)
):
    return await archive_deceased(db, deceased_id, archive_in.archived)
