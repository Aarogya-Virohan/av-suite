from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.dependencies import (
    AuthenticatedContextDep,
    get_current_user,
    require_capability,
)
from app.enums.permission import CapabilityScope
from app.models.user import User
from app.models.membership import Membership
from app.schemas.user import UserRead, UserCreate
from app.core.security import get_password_hash
from app.schemas.envelope import ResponseEnvelope
from app.repositories.user_permission import UserPermissionRepository
from app.schemas.user_permission import UserPermissionRead, UserPermissionCreate
from app.enums.user import UserRole
from app.repositories.audit import AuditLogRepository
from app.services.audit import AuditLogService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[List[UserRead]], tags=["Users"])
async def list_users(
    auth_context: AuthenticatedContextDep,
    db: AsyncSession = Depends(get_db),
    scope: CapabilityScope = Depends(require_capability("users.view")),
):
    """
    List all users/therapists in the clinic.
    """
    clinic_id = auth_context.clinic.id

    stmt = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.clinic_id == clinic_id)
        .order_by(User.created_at, User.id)
    )
    users = (await db.execute(stmt)).all()
    
    # We must return dicts with 'name' since User doesn't have it.
    users_data = []
    for user, role in users:
        u_dict = {
            "id": user.id,
            "clinic_id": clinic_id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        users_data.append(u_dict)
        
    return ResponseEnvelope(data=users_data)


@router.post("", response_model=ResponseEnvelope[UserRead], status_code=201, tags=["Users"])
async def create_user(
    payload: UserCreate, 
    auth_context: AuthenticatedContextDep,
    db: AsyncSession = Depends(get_db),
    scope: CapabilityScope = Depends(require_capability("users.create")),
):
    """
    Create a new user in the clinic.
    """
    clinic_id = auth_context.clinic.id
    
    # Extract first/last name if only name is provided
    fname = payload.first_name
    lname = payload.last_name
    
    if not fname and not lname and payload.name:
        parts = payload.name.split(" ", 1)
        fname = parts[0]
        lname = parts[1] if len(parts) > 1 else ""
        
    try:
        new_user = await db.scalar(
            select(User).where(User.email == payload.email).with_for_update()
        )
        if new_user is None:
            new_user = User(
                clinic_id=clinic_id,
                email=payload.email,
                password_hash=get_password_hash(payload.password),
                first_name=fname or "",
                last_name=lname or "",
                phone=payload.phone,
                role=payload.role,
                is_active=payload.is_active,
            )
            db.add(new_user)
            await db.flush()

        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == new_user.id,
                Membership.clinic_id == clinic_id,
            )
        )
        if membership is None:
            membership = Membership(
                user_id=new_user.id,
                clinic_id=clinic_id,
                role=payload.role,
            )
            db.add(membership)
            await db.flush()
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        # Concurrent duplicate submissions may race on the user or membership
        # uniqueness constraints. Re-read the committed rows and accept only
        # when this exact workspace membership now exists.
        new_user = await db.scalar(select(User).where(User.email == payload.email))
        if new_user is None:
            raise HTTPException(status_code=409, detail="User creation conflicted")
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == new_user.id,
                Membership.clinic_id == clinic_id,
            )
        )
        if membership is None:
            membership = Membership(
                user_id=new_user.id,
                clinic_id=clinic_id,
                role=payload.role,
            )
            db.add(membership)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                membership = await db.scalar(
                    select(Membership).where(
                        Membership.user_id == new_user.id,
                        Membership.clinic_id == clinic_id,
                    )
                )
                if membership is None:
                    raise HTTPException(
                        status_code=409, detail="Membership creation conflicted"
                    )
        await db.refresh(new_user)
    
    # Add name field for UserRead compatibility
    u_dict = {
        "id": new_user.id,
        "clinic_id": clinic_id,
        "name": f"{new_user.first_name} {new_user.last_name}".strip(),
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "email": new_user.email,
        "phone": new_user.phone,
        "role": membership.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at
    }
    
    return ResponseEnvelope(data=u_dict)


@router.get("/{user_id}/permissions", response_model=ResponseEnvelope[List[UserPermissionRead]], tags=["Users"])
async def get_user_permissions(
    user_id: UUID,
    auth_context: AuthenticatedContextDep,
    db: AsyncSession = Depends(get_db),
    scope: CapabilityScope = Depends(require_capability("permissions.view")),
):
    """
    Get all explicit permission overrides for a user in the clinic.
    """
    clinic_id = auth_context.clinic.id
    repo = UserPermissionRepository(db)
    
    # Verify user belongs to clinic
    user_stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(User.id == user_id, Membership.clinic_id == clinic_id)
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    permissions = await repo.list_for_user_in_clinic(clinic_id, user_id)
    return ResponseEnvelope(data=permissions)


@router.put("/{user_id}/permissions", response_model=ResponseEnvelope[List[UserPermissionRead]], tags=["Users"])
async def update_user_permissions(
    user_id: UUID, 
    permissions: List[UserPermissionCreate], 
    auth_context: AuthenticatedContextDep,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: CapabilityScope = Depends(require_capability("permissions.edit")),
):
    """
    Completely replace the user's explicit permission overrides.
    Any existing override not in this list will be removed.
    """
    clinic_id = auth_context.clinic.id
    repo = UserPermissionRepository(db)
    
    # Verify user belongs to clinic
    user_stmt = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(User.id == user_id, Membership.clinic_id == clinic_id)
    )
    user_row = (await db.execute(user_stmt)).first()
    user, target_role = user_row if user_row else (None, None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    granted_by = current_user.id
    
    # Lockout Guard: Prevent removing 'permissions.edit' or 'users.edit' capability from last admin
    new_perms_override = next((p.scope for p in permissions if p.capability_key in ('permissions.edit', 'permissions.manage')), None)
    new_users_override = next((p.scope for p in permissions if p.capability_key in ('users.edit', 'users.manage')), None)
    
    # We only care if they are explicitly being set to 'none' and target is currently an Admin
    if target_role == UserRole.ADMIN and (new_perms_override == 'none' or new_users_override == 'none'):
        # Check if any OTHER active admin exists without a 'none' override
        all_admins_stmt = (
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.clinic_id == clinic_id,
                Membership.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.id != user_id,
            )
        )
        other_admins = (await db.execute(all_admins_stmt)).scalars().all()
        
        has_other_admin_with_perms = False
        for admin in other_admins:
            admin_overrides = await repo.list_for_user_in_clinic(clinic_id, admin.id)
            perms_override = next((p.scope for p in admin_overrides if p.capability_key in ('permissions.edit', 'permissions.manage')), None)
            users_override = next((p.scope for p in admin_overrides if p.capability_key in ('users.edit', 'users.manage')), None)
            
            # If the other admin does not have a 'none' override for either, they are safe
            if perms_override != 'none' and users_override != 'none':
                has_other_admin_with_perms = True
                break
                
        if not has_other_admin_with_perms:
            raise HTTPException(status_code=400, detail="Lockout Guard: Cannot revoke permissions/users management capability from the last clinic administrator.")
    
    # Setup audit service
    audit_service = AuditLogService(AuditLogRepository(db))
    
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
        await audit_service.log_event(
            clinic_id=clinic_id,
            user_id=granted_by,
            action="revoke_permission",
            entity_type="user_permissions",
            entity_id=user_id,
            details={"capability_key": key_to_delete, "target_user_id": str(user_id)}
        )
        
    # Upsert the provided overrides
    updated_perms = []
    for p in permissions:
        # Check if it changed or is new
        existing_perm = next((e for e in existing if e.capability_key == p.capability_key), None)
        if not existing_perm or existing_perm.scope != p.scope:
            perm = await repo.set_override(
                clinic_id=clinic_id,
                user_id=user_id,
                capability_key=p.capability_key,
                scope=p.scope,
                granted_by=granted_by
            )
            updated_perms.append(perm)
            await audit_service.log_event(
                clinic_id=clinic_id,
                user_id=granted_by,
                action="grant_permission",
                entity_type="user_permissions",
                entity_id=user_id,
                details={"capability_key": p.capability_key, "scope": p.scope, "target_user_id": str(user_id)}
            )
        else:
            updated_perms.append(existing_perm)
        
    await db.commit()
    
    return ResponseEnvelope(data=updated_perms)


@router.delete("/{user_id}", response_model=ResponseEnvelope[None], tags=["Users"])
async def delete_user(
    user_id: UUID,
    auth_context: AuthenticatedContextDep,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: CapabilityScope = Depends(require_capability("users.delete")),
):
    """
    Remove a user from the clinic.
    """
    clinic_id = auth_context.clinic.id
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself.")
        
    user_stmt = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(User.id == user_id, Membership.clinic_id == clinic_id)
    )
    user_row = (await db.execute(user_stmt)).first()
    user, target_role = user_row if user_row else (None, None)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent deleting the last admin
    if target_role == UserRole.ADMIN:
        all_admins_stmt = (
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.clinic_id == clinic_id,
                Membership.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.id != user_id,
            )
        )
        other_admins = (await db.execute(all_admins_stmt)).scalars().all()
        if not other_admins:
            raise HTTPException(status_code=400, detail="Cannot remove the last clinic administrator.")
            
    membership = await db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.clinic_id == clinic_id,
        )
    )
    await db.delete(membership)
    for permission in await UserPermissionRepository(db).list_for_user_in_clinic(
        clinic_id, user_id
    ):
        await db.delete(permission)
    
    # Audit log
    audit_service = AuditLogService(AuditLogRepository(db))
    await audit_service.log_event(
        clinic_id=clinic_id,
        user_id=current_user.id,
        action="delete_user",
        entity_type="users",
        entity_id=user_id,
        details={"deleted_user_email": user.email, "deleted_user_role": target_role}
    )
    
    await db.commit()
    return ResponseEnvelope(data=None)
