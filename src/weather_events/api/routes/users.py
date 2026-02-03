"""User management routes."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.auth.dependencies import get_current_user, require_admin
from weather_events.database.connection import get_db_session
from weather_events.database.models import User

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    name: str | None
    picture_url: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None


class UserListResponse(BaseModel):
    """User list response."""

    users: list[UserResponse]
    total: int


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the current user's profile."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.delete("/me")
async def delete_current_user(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete the current user's account.

    This permanently deletes the user and all associated data.
    """
    await db.delete(user)
    await db.commit()

    return {"status": "deleted"}


# Admin routes


@router.get("/", response_model=UserListResponse)
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 50,
) -> UserListResponse:
    """List all users (admin only)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    # Get total count
    count_result = await db.execute(select(User))
    total = len(count_result.scalars().all())

    return UserListResponse(
        users=[
            UserResponse(
                id=str(u.id),
                email=u.email,
                name=u.name,
                picture_url=u.picture_url,
                is_active=u.is_active,
                is_admin=u.is_admin,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
            for u in users
        ],
        total=total,
    )


@router.patch("/{user_id}/admin")
async def toggle_admin(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Toggle admin status for a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent removing own admin
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin status",
        )

    user.is_admin = not user.is_admin
    await db.commit()

    return {"is_admin": user.is_admin}
