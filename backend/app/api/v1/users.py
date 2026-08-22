from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.user import UserRead
from app.schemas.envelope import ResponseEnvelope
from app.repositories.user_permission import UserPermissionRepository
from app.schemas.user_permission import UserPermissionRead, UserPermissionCreate

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_permission("clinic_admin"))])

@router.get("", response_model=ResponseEnvelope[List[UserRead]], tags=["Users"])
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    """
    List all users/therapists in the clinic.
    """
    clinic_id = request.state.clinic_id
    
    stmt = select(User).where(User.clinic_id == clinic_id)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # We must return dicts with 'name' since User doesn't have it.
    users_data = []
    for user in users:
        u_dict = {
            "id": user.id,
            "clinic_id": user.clinic_id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        users_data.append(u_dict)
        
    return ResponseEnvelope(data=users_data)


@router.get("/{user_id}/permissions", response_model=ResponseEnvelope[List[UserPermissionRead]], tags=["Users"])
async def get_user_permissions(user_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Get all explicit permission overrides for a user in the clinic.
    """
    clinic_id = request.state.clinic_id
    repo = UserPermissionRepository(db)
    
    # Verify user belongs to clinic
    user_stmt = select(User).where(User.id == user_id, User.clinic_id == clinic_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    permissions = await repo.list_for_user_in_clinic(clinic_id, user_id)
    return ResponseEnvelope(data=permissions)


@router.put("/{user_id}/permissions", response_model=ResponseEnvelope[List[UserPermissionRead]], tags=["Users"])
async def update_user_permissions(
    user_id: UUID, 
    permissions: List[UserPermissionCreate], 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    Completely replace the user's explicit permission overrides.
    Any existing override not in this list will be removed.
    """
    clinic_id = request.state.clinic_id
    repo = UserPermissionRepository(db)
    
    # Verify user belongs to clinic
    user_stmt = select(User).where(User.id == user_id, User.clinic_id == clinic_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    granted_by = request.state.user.id if hasattr(request.state, "user") and request.state.user else None
    
    # Get existing overrides
    existing = await repo.list_for_user_in_clinic(clinic_id, user_id)
    existing_keys = {e.capability_key for e in existing}
    new_keys = {p.capability_key for p in permissions}
    
    # Delete overrides that are not in the new payload
    for key_to_delete in existing_keys - new_keys:
        await repo.delete_for_user_capability(
            clinic_id=clinic_id,
            user_id=user_id,
            capability_key=key_to_delete
        )
        
    # Upsert the provided overrides
    updated_perms = []
    for p in permissions:
        perm = await repo.set_override(
            clinic_id=clinic_id,
            user_id=user_id,
            capability_key=p.capability_key,
            scope=p.scope,
            granted_by=granted_by
        )
        updated_perms.append(perm)
        
    await db.commit()
    
    return ResponseEnvelope(data=updated_perms)
