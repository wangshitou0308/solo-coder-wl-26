from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.core.roles import UserRole
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import get_dashboard

router = APIRouter(prefix="/dashboard", tags=["状态追踪看板"])


@router.get(
    "",
    response_model=DashboardResponse,
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db)
):
    return await get_dashboard(db)
