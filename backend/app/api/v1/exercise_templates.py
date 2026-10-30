"""Exercise templates (EL-D-009).

Read needs exercises.view; writes need prescriptions.create, since a template
is a saved starting point for prescriptions. No new capability, so no role
template changes. AV templates (clinic_id NULL) are read-only for clinics.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.exercises import _user_id, _with_photos
from app.core.database import get_db
from app.core.dependencies import require_capability
from app.schemas.envelope import ResponseEnvelope
from app.schemas.exercise_template import TemplateIn, TemplateItemRead, TemplateRead
from app.services import exercise_template_service as svc

router = APIRouter()

NOT_FOUND = "Template not found"
GLOBAL_READ_ONLY = "This template is part of the AV library and cannot be changed by a clinic."


def _clinic(request: Request) -> uuid.UUID:
    return uuid.UUID(str(request.state.clinic_id))


async def _read(db: AsyncSession, clinic_id: uuid.UUID, templates) -> List[TemplateRead]:
    """TemplateRead rows; each exercise carries its categories and the
    clinic's photos, like the library list."""
    exercises = {it.exercise.id: it.exercise for t in templates for it in t.items if it.exercise}
    enriched = {e.id: e for e in await _with_photos(db, clinic_id, list(exercises.values()))}
    out = []
    for t in templates:
        items = []
        for it in t.items:
            row = TemplateItemRead.model_validate(it)
            row.exercise = enriched.get(it.exercise_id)
            items.append(row)
        out.append(
            TemplateRead(
                id=t.id,
                clinic_id=t.clinic_id,
                name=t.name,
                description=t.description,
                is_global=t.clinic_id is None,
                created_at=t.created_at,
                updated_at=t.updated_at,
                items=items,
            )
        )
    return out


@router.get("", response_model=ResponseEnvelope[List[TemplateRead]], tags=["Exercise templates"])
async def list_templates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_capability("exercises.view")),
):
    clinic_id = _clinic(request)
    return ResponseEnvelope(data=await _read(db, clinic_id, await svc.list_templates(db, clinic_id)))


@router.get("/{template_id}", response_model=ResponseEnvelope[TemplateRead], tags=["Exercise templates"])
async def get_template(
    request: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_capability("exercises.view")),
):
    clinic_id = _clinic(request)
    template = await svc.get_template(db, clinic_id, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return ResponseEnvelope(data=(await _read(db, clinic_id, [template]))[0])


@router.post("", response_model=ResponseEnvelope[TemplateRead], status_code=201, tags=["Exercise templates"])
async def create_template(
    request: Request,
    data: TemplateIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_capability("prescriptions.create")),
):
    clinic_id = _clinic(request)
    try:
        template = await svc.create_template(db, clinic_id, _user_id(request), data)
    except svc.TemplateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ResponseEnvelope(data=(await _read(db, clinic_id, [template]))[0])


@router.put("/{template_id}", response_model=ResponseEnvelope[TemplateRead], tags=["Exercise templates"])
async def update_template(
    request: Request,
    template_id: uuid.UUID,
    data: TemplateIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_capability("prescriptions.create")),
):
    clinic_id = _clinic(request)
    try:
        template = await svc.update_template(db, clinic_id, template_id, data)
    except svc.GlobalTemplateReadOnly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_READ_ONLY)
    except svc.TemplateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return ResponseEnvelope(data=(await _read(db, clinic_id, [template]))[0])


@router.delete("/{template_id}", response_model=ResponseEnvelope[dict], tags=["Exercise templates"])
async def delete_template(
    request: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_capability("prescriptions.create")),
):
    clinic_id = _clinic(request)
    try:
        deleted = await svc.delete_template(db, clinic_id, template_id)
    except svc.GlobalTemplateReadOnly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_READ_ONLY)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return ResponseEnvelope(data={"message": "Template deleted."})
