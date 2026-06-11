from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.deceased import Deceased
from app.models.family_relation import FamilyRelation
from app.schemas.deceased import DeceasedCreate, DeceasedUpdate


async def get_deceased_by_id(db: AsyncSession, deceased_id: int):
    result = await db.execute(
        select(Deceased)
        .options(joinedload(Deceased.family_relations))
        .where(Deceased.id == deceased_id)
    )
    deceased = result.unique().scalar_one_or_none()
    if not deceased:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="逝者档案不存在"
        )
    return deceased


async def create_deceased(db: AsyncSession, deceased_in: DeceasedCreate, created_by: int):
    existing = await db.execute(
        select(Deceased).where(Deceased.id_card == deceased_in.id_card)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该身份证号的逝者档案已存在"
        )

    deceased = Deceased(
        **deceased_in.model_dump(exclude={"family_relations"})
    )
    db.add(deceased)
    await db.flush()

    for rel in deceased_in.family_relations:
        family_rel = FamilyRelation(
            deceased_id=deceased.id,
            **rel.model_dump()
        )
        db.add(family_rel)

    await db.commit()
    await db.refresh(deceased)
    return await get_deceased_by_id(db, deceased.id)


async def update_deceased(db: AsyncSession, deceased_id: int, deceased_in: DeceasedUpdate):
    deceased = await get_deceased_by_id(db, deceased_id)

    if deceased.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该逝者档案已归档，无法修改"
        )

    update_data = deceased_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deceased, field, value)

    await db.commit()
    await db.refresh(deceased)
    return await get_deceased_by_id(db, deceased_id)


async def archive_deceased(db: AsyncSession, deceased_id: int, archived: bool = True):
    deceased = await get_deceased_by_id(db, deceased_id)
    deceased.is_archived = archived
    deceased.archived_at = datetime.utcnow() if archived else None
    await db.commit()
    await db.refresh(deceased)
    return await get_deceased_by_id(db, deceased_id)


async def list_deceased(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    name: str | None = None,
    id_card: str | None = None
):
    query = select(Deceased).options(joinedload(Deceased.family_relations))

    if not include_archived:
        query = query.where(Deceased.is_archived == False)

    if name:
        query = query.where(Deceased.name.ilike(f"%{name}%"))
    if id_card:
        query = query.where(Deceased.id_card == id_card)

    query = query.offset(skip).limit(limit).order_by(Deceased.created_at.desc())
    result = await db.execute(query)
    return result.unique().scalars().all()


async def get_in_house_count(db: AsyncSession):
    from app.models.cremation import CremationQueue, CremationStatus
    result = await db.execute(
        select(func.count(Deceased.id))
        .join(CremationQueue, Deceased.id == CremationQueue.deceased_id)
        .where(
            Deceased.is_archived == False,
            CremationStatus.ASHES_COLLECTED != CremationStatus.ASHES_COLLECTED
        )
    )
    return result.scalar() or 0


async def get_today_new_count(db: AsyncSession):
    today = datetime.utcnow().date()
    result = await db.execute(
        select(func.count(Deceased.id))
        .where(func.date(Deceased.created_at) == today)
    )
    return result.scalar() or 0


async def get_today_completed_services(db: AsyncSession):
    from app.models.cremation import CremationQueue, CremationStatus
    today = datetime.utcnow().date()
    result = await db.execute(
        select(func.count(CremationQueue.id))
        .where(
            func.date(CremationQueue.collected_at) == today,
            CremationQueue.status == CremationStatus.ASHES_COLLECTED
        )
    )
    return result.scalar() or 0
