from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleChecker
from app.core.roles import UserRole
from app.models.user import User
from app.schemas.auth import (
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
    ChangePassword,
)
from app.services.auth_service import (
    authenticate_user,
    create_user_token,
    create_user,
    update_user,
    get_user_by_id,
    list_users,
    change_password,
    get_users_by_role,
)

router = APIRouter(prefix="/auth", tags=["认证与用户管理"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await create_user_token(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.post("/change-password")
async def change_user_password(
    password_in: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await change_password(db, current_user.id, password_in)
    return {"success": True, "message": "密码修改成功"}


@router.post(
    "/users",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def create_new_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_user(db, user_in)


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def get_users(
    role: UserRole | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await list_users(db, role, skip, limit)


@router.get(
    "/users/drivers",
    response_model=list[UserResponse]
)
async def get_drivers_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_users_by_role(db, UserRole.DRIVER)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(UserRole.DIRECTOR))]
)
async def update_user_info(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_user(db, user_id, user_in)
