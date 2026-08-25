from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from app.core.database import get_db
from app.core.dependencies import require_capability
from app.models.user import User
from app.schemas.user import UserRead
from app.schemas.envelope import ResponseEnvelope

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_capability("therapists.view"))])


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
            "updated_at": user.updated_at,
        }
        users_data.append(u_dict)

    return ResponseEnvelope(data=users_data)
