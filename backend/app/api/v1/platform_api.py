from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import SessionDep, get_client_ip, get_platform_operator
from app.core.platform_rbac import require_platform_permission
from app.enums.product import EntitlementSource, EntitlementStatus
from app.enums.user import UserRole
from app.exceptions import BaseAppException
from app.schemas.envelope import ResponseEnvelope
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.platform import PlatformAuditLog, PlatformOperator
from app.models.product import Product, WorkspaceProduct
from app.models.usage_event import UsageEvent
from app.services.platform_audit import record_platform_audit
from app.services.product_entitlements import active_entitlement_clause, ensure_canonical_products

router = APIRouter()

class ReasonBody(BaseModel):
    reason: str | None = None

class OrganizationCreateBody(ReasonBody):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120)
    type: Literal["individual", "clinic", "chain", "franchise", "hospital", "government", "partner_platform"]
    contact_email: str | None = None
    contact_phone: str | None = None

class OrganizationUpdateBody(ReasonBody):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: Literal["individual", "clinic", "chain", "franchise", "hospital", "government", "partner_platform"] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None

class ClinicCreateBody(ReasonBody):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120)
    type: Literal["clinic", "solo", "personal"]

class MergeBody(ReasonBody):
    source_organization_id: UUID

class EntitlementBody(ReasonBody):
    status: str
    valid_from: datetime | None
    valid_until: datetime | None

class OperatorUpdateBody(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    reason: str | None = None

class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; name: str; slug: str; type: str; status: str
    contact_email: str | None; contact_phone: str | None
    created_at: datetime; updated_at: datetime

class ClinicOut(BaseModel):
    id: UUID; organization_id: UUID; name: str; slug: str; type: str; status: str
    staff_count: int; last_activity_at: datetime | None; created_at: datetime

class EntitlementOut(BaseModel):
    product_key: str; status: str; source: str; valid_from: datetime | None
    valid_until: datetime | None; is_effective: bool; updated_at: datetime

class OperatorOut(BaseModel):
    id: UUID; email: str; name: str; role: str; is_active: bool; mfa_enabled: bool
    last_login_at: datetime | None; created_at: datetime; updated_at: datetime



class OrganizationListOut(OrganizationOut):
    clinic_count: int
    active_clinic_count: int

class OrganizationDetailOut(OrganizationOut):
    clinics: list[ClinicOut]

class ProductCatalogOut(BaseModel):
    key: str
    name: str
    description: str
    category: str

class ClinicUsageOut(BaseModel):
    window_days: int
    total_events: int
    by_product: list[dict[str, Any]]

class ClinicDetailOut(ClinicOut):
    organization_name: str
    organization_status: str
    products: list[EntitlementOut]
    usage: ClinicUsageOut

class UsageRowOut(BaseModel):
    date: date
    clinic_id: UUID
    product_key: str
    event_type: str
    count: int

class AuditLogOut(BaseModel):
    id: UUID
    operator_id: UUID | None
    operator_name: str | None
    action: str
    target_type: str
    target_id: str | None
    target_name: str | None
    organization_id: UUID | None
    clinic_id: UUID | None
    reason: str | None
    ip: str | None
    user_agent: str | None
    details: dict[str, Any]
    created_at: datetime

class OrganizationCountsOut(BaseModel):
    total: int
    active: int
    suspended: int
    by_type: dict[str, int]

class ClinicCountsOut(BaseModel):
    total: int
    active: int
    suspended: int

class ProductCountOut(BaseModel):
    product_key: str
    effective_clinics: int

class OverviewOut(BaseModel):
    organizations: OrganizationCountsOut
    clinics: ClinicCountsOut
    products: list[ProductCountOut]
    usage_last_30_days: int
    recent_audit: list[AuditLogOut]

def _reason(body: Any) -> str:
    reason = getattr(body, "reason", None)
    if not isinstance(reason, str) or not reason.strip():
        raise BaseAppException("Reason is required", "VALIDATION_ERROR", 422)
    return reason.strip()

def _audit(db, request, actor, *, action, target_type, target_id, reason, before, after, organization_id=None, clinic_id=None):
    record_platform_audit(db, operator_id=actor.id, action=action, target_type=target_type,
        target_id=target_id, reason=reason, ip=get_client_ip(request),
        user_agent=request.headers.get("user-agent"), details=jsonable_encoder({"before": before, "after": after}),
        organization_id=organization_id, clinic_id=clinic_id)

def _org(o):
    return {"id":o.id,"name":o.name,"slug":o.slug,"type":o.type,"status":o.status,"contact_email":o.contact_email,"contact_phone":o.contact_phone,"created_at":o.created_at,"updated_at":o.updated_at}

async def _clinic_row(db, c):
    staff = await db.scalar(select(func.count(Membership.id)).where(Membership.clinic_id == c.id, Membership.role != UserRole.PATIENT)) or 0
    last = await db.scalar(select(func.max(UsageEvent.created_at)).where(UsageEvent.clinic_id == c.id))
    return {"id":c.id,"organization_id":c.organization_id,"name":c.name,"slug":c.slug,"type":c.type.value if hasattr(c.type,"value") else c.type,"status":c.status,"staff_count":staff,"last_activity_at":last,"created_at":c.created_at}

async def _flush_new(db, obj):
    try:
        async with db.begin_nested():
            db.add(obj)
            await db.flush()
    except IntegrityError:
        raise BaseAppException("Slug already in use", "CONFLICT", 409)

async def _target_name(db, a):
    try:
        if a.target_type=="organization" and a.target_id: return await db.scalar(select(Organization.name).where(Organization.id==UUID(a.target_id)))
        if a.target_type in ("clinic","entitlement") and a.clinic_id: return await db.scalar(select(Clinic.name).where(Clinic.id==a.clinic_id))
        if a.target_type=="operator" and a.target_id: return await db.scalar(select(PlatformOperator.name).where(PlatformOperator.id==UUID(a.target_id)))
    except ValueError:
        return None
    return None

async def _page(db, stmt, count_stmt, page, page_size):
    total = await db.scalar(count_stmt) or 0
    rows = (await db.execute(stmt.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return rows, {"total":total,"page":page,"page_size":page_size}

@router.get("/products", response_model=ResponseEnvelope[list[ProductCatalogOut]])
async def products(db: SessionDep, _: PlatformOperator = Depends(get_platform_operator)):
    await ensure_canonical_products(db)
    await db.flush()
    rows = (await db.execute(select(Product).where(Product.is_active.is_(True), Product.id != "clinical-decision-support").order_by(Product.name))).scalars().all()
    return {"data":[{"key":p.id,"name":p.name,"description":p.description or "","category":p.category or ""} for p in rows],"meta":{}}

@router.get("/organizations", response_model=ResponseEnvelope[list[OrganizationListOut]])
async def organizations(db: SessionDep, search: str|None=None, type: str|None=None, status: str|None=None, page:int=Query(1,ge=1), page_size:int=Query(20,ge=1,le=100), _:PlatformOperator=Depends(require_platform_permission("platform.organizations.read"))):
    filt=[]
    if search: filt.append(or_(Organization.name.ilike(f"%{search}%"),Organization.slug.ilike(f"%{search}%")))
    if type: filt.append(Organization.type==type)
    if status: filt.append(Organization.status==status)
    q=select(Organization).where(*filt).order_by(Organization.created_at.desc(),Organization.id)
    rows,meta=await _page(db,q,select(func.count(Organization.id)).where(*filt),page,page_size)
    data=[]
    for o in rows:
        total=await db.scalar(select(func.count(Clinic.id)).where(Clinic.organization_id==o.id)) or 0
        active=await db.scalar(select(func.count(Clinic.id)).where(Clinic.organization_id==o.id,Clinic.status=="active")) or 0
        data.append({**_org(o),"clinic_count":total,"active_clinic_count":active})
    return {"data":data,"meta":meta}

@router.post("/organizations", response_model=ResponseEnvelope[OrganizationOut])
async def create_organization(body:OrganizationCreateBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):
    reason=_reason(body); o=Organization(name=body.name,slug=body.slug,type=body.type,contact_email=body.contact_email,contact_phone=body.contact_phone,status="active")
    await _flush_new(db,o); after=_org(o); _audit(db,request,actor,action="organization.created",target_type="organization",target_id=o.id,reason=reason,before=None,after=after,organization_id=o.id)
    return {"data":after,"meta":{}}

@router.get("/organizations/{org_id}", response_model=ResponseEnvelope[OrganizationDetailOut])
async def get_organization(org_id:UUID,db:SessionDep,_:PlatformOperator=Depends(require_platform_permission("platform.organizations.read"))):
    o=await db.get(Organization,org_id)
    if not o: raise BaseAppException("Organization not found","NOT_FOUND",404)
    clinics=(await db.scalars(select(Clinic).where(Clinic.organization_id==org_id).order_by(Clinic.created_at))).all()
    return {"data":{**_org(o),"clinics":[await _clinic_row(db,c) for c in clinics]},"meta":{}}

@router.patch("/organizations/{org_id}", response_model=ResponseEnvelope[OrganizationOut])
async def update_organization(org_id:UUID,body:OrganizationUpdateBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):
    reason=_reason(body); o=await db.get(Organization,org_id)
    if not o: raise BaseAppException("Organization not found","NOT_FOUND",404)
    before=_org(o)
    for key in ("name","type","contact_email","contact_phone"):
        val=getattr(body,key)
        if key in body.model_fields_set and (val is not None or key in {"contact_email", "contact_phone"}): setattr(o,key,val)
    await db.flush(); await db.refresh(o); after=_org(o); _audit(db,request,actor,action="organization.updated",target_type="organization",target_id=o.id,reason=reason,before=before,after=after,organization_id=o.id)
    return {"data":after,"meta":{}}

async def _set_org_status(org_id, new_status, body, request, db, actor):
    reason=_reason(body); o=await db.get(Organization,org_id)
    if not o: raise BaseAppException("Organization not found","NOT_FOUND",404)
    before=_org(o); o.status=new_status; await db.flush(); await db.refresh(o); after=_org(o)
    _audit(db,request,actor,action=f"organization.{new_status}",target_type="organization",target_id=o.id,reason=reason,before=before,after=after,organization_id=o.id)
    return {"data":after,"meta":{}}

@router.post("/organizations/{org_id}/suspend", response_model=ResponseEnvelope[OrganizationOut])
async def suspend_org(org_id:UUID,body:ReasonBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))): return await _set_org_status(org_id,"suspended",body,request,db,actor)
@router.post("/organizations/{org_id}/activate", response_model=ResponseEnvelope[OrganizationOut])
async def activate_org(org_id:UUID,body:ReasonBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))): return await _set_org_status(org_id,"active",body,request,db,actor)

@router.post("/organizations/{org_id}/clinics", response_model=ResponseEnvelope[ClinicOut])
async def create_clinic(org_id:UUID,body:ClinicCreateBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):
    reason=_reason(body); o=await db.get(Organization,org_id)
    if not o: raise BaseAppException("Organization not found","NOT_FOUND",404)
    c=Clinic(name=body.name,slug=body.slug,type=body.type,organization_id=o.id,status="active")
    await _flush_new(db,c); after=await _clinic_row(db,c)
    _audit(db,request,actor,action="clinic.created",target_type="clinic",target_id=c.id,reason=reason,before=None,after=after,organization_id=o.id,clinic_id=c.id)
    return {"data":after,"meta":{}}

@router.get("/clinics/{clinic_id}", response_model=ResponseEnvelope[ClinicDetailOut])
async def get_clinic(clinic_id:UUID,db:SessionDep,_:PlatformOperator=Depends(require_platform_permission("platform.organizations.read"))):
    c=await db.get(Clinic,clinic_id)
    if not c: raise BaseAppException("Clinic not found","NOT_FOUND",404)
    org=await db.get(Organization,c.organization_id)
    products=(await db.execute(select(WorkspaceProduct,Product).join(Product,Product.id==WorkspaceProduct.product_id).where(WorkspaceProduct.clinic_id==c.id))).all()
    now=datetime.now(timezone.utc); ent=[]
    for w,p in products:
        ent.append({"product_key":p.id,"status":w.status.value,"source":w.source.value,"valid_from":w.valid_from,"valid_until":w.valid_until,"is_effective":bool((await db.scalar(select(WorkspaceProduct.id).where(WorkspaceProduct.id==w.id,active_entitlement_clause(now))))),"updated_at":w.updated_at})
    summary=(await db.execute(select(UsageEvent.product_key,func.count(UsageEvent.id)).where(UsageEvent.clinic_id==c.id,UsageEvent.created_at>=now-timedelta(days=30)).group_by(UsageEvent.product_key))).all()
    return {"data":{**await _clinic_row(db,c),"organization_name":org.name,"organization_status":org.status,"products":ent,"usage":{"window_days":30,"total_events":sum(n for _,n in summary),"by_product":[{"product_key":k,"events":n} for k,n in summary]}},"meta":{}}

async def _set_clinic_status(clinic_id,new_status,body,request,db,actor):
    reason=_reason(body); c=await db.get(Clinic,clinic_id)
    if not c: raise BaseAppException("Clinic not found","NOT_FOUND",404)
    before=await _clinic_row(db,c); c.status=new_status; await db.flush(); after=await _clinic_row(db,c)
    _audit(db,request,actor,action=f"clinic.{new_status}",target_type="clinic",target_id=c.id,reason=reason,before=before,after=after,organization_id=c.organization_id,clinic_id=c.id)
    return {"data":after,"meta":{}}
@router.post("/clinics/{clinic_id}/suspend", response_model=ResponseEnvelope[ClinicOut])
async def suspend_clinic(clinic_id:UUID,body:ReasonBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):return await _set_clinic_status(clinic_id,"suspended",body,request,db,actor)
@router.post("/clinics/{clinic_id}/activate", response_model=ResponseEnvelope[ClinicOut])
async def activate_clinic(clinic_id:UUID,body:ReasonBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):return await _set_clinic_status(clinic_id,"active",body,request,db,actor)

@router.post("/organizations/{org_id}/merge", response_model=ResponseEnvelope[OrganizationDetailOut])
async def merge_organization(org_id:UUID,body:MergeBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.organizations.manage"))):
    reason=_reason(body)
    if org_id==body.source_organization_id: raise BaseAppException("Source and target must differ","VALIDATION_ERROR",422)
    target=await db.scalar(select(Organization).where(Organization.id==org_id).with_for_update()); source=await db.scalar(select(Organization).where(Organization.id==body.source_organization_id).with_for_update())
    if not target or not source: raise BaseAppException("Organization not found","NOT_FOUND",404)
    clinics=(await db.scalars(select(Clinic).where(Clinic.organization_id==source.id).with_for_update())).all()
    before={"target":_org(target),"source":_org(source),"clinic_ids":[str(c.id) for c in clinics]}
    for c in clinics:c.organization_id=target.id
    await db.flush(); after={"target":_org(target),"source":_org(source),"clinic_ids":[str(c.id) for c in clinics]}
    _audit(db,request,actor,action="organization.merged",target_type="organization",target_id=target.id,reason=reason,before=before,after=after,organization_id=target.id)
    rows=(await db.scalars(select(Clinic).where(Clinic.organization_id==target.id).order_by(Clinic.created_at))).all()
    return {"data":{**_org(target),"clinics":[await _clinic_row(db,c) for c in rows]},"meta":{}}

@router.put("/clinics/{clinic_id}/products/{product_key}", response_model=ResponseEnvelope[EntitlementOut])
async def set_entitlement(clinic_id:UUID,product_key:str,body:EntitlementBody,request:Request,db:SessionDep,actor:PlatformOperator=Depends(require_platform_permission("platform.entitlements.manage"))):
    reason=_reason(body)
    await ensure_canonical_products(db)
    await db.flush()
    if body.status not in {"enabled","disabled"}: raise BaseAppException("Invalid entitlement status","VALIDATION_ERROR",422)
    if body.valid_from and body.valid_until and body.valid_until<=body.valid_from: raise BaseAppException("valid_until must be after valid_from","VALIDATION_ERROR",422)
    c=await db.get(Clinic,clinic_id); p=await db.get(Product,product_key)
    if not c or not p: raise BaseAppException("Clinic or product not found","NOT_FOUND",404)
    now=datetime.now(timezone.utc)
    w=await db.scalar(select(WorkspaceProduct).where(WorkspaceProduct.clinic_id==c.id,WorkspaceProduct.product_id==p.id).with_for_update())
    if w is None:
        before=None
        w=WorkspaceProduct(clinic_id=c.id,product_id=p.id)
    else:
        before={"product_key":p.id,"status":w.status.value,"source":w.source.value,"valid_from":w.valid_from,"valid_until":w.valid_until,"is_effective":bool(await db.scalar(select(WorkspaceProduct.id).where(WorkspaceProduct.id==w.id,active_entitlement_clause(now)))),"updated_at":w.updated_at}
    w.status=EntitlementStatus(body.status);w.source=EntitlementSource.DIRECT;w.bundle_id=None;w.valid_from=body.valid_from;w.valid_until=body.valid_until
    db.add(w);await db.flush();await db.refresh(w)
    after={"product_key":p.id,"status":w.status.value,"source":w.source.value,"valid_from":w.valid_from,"valid_until":w.valid_until,"is_effective":bool(await db.scalar(select(WorkspaceProduct.id).where(WorkspaceProduct.id==w.id,active_entitlement_clause(now)))),"updated_at":w.updated_at}
    _audit(db,request,actor,action="entitlement.updated",target_type="entitlement",target_id=f"{c.id}:{p.id}",reason=reason,before=before,after=after,organization_id=c.organization_id,clinic_id=c.id)
    return {"data":after,"meta":{}}

@router.get("/usage", response_model=ResponseEnvelope[list[UsageRowOut]])
async def usage(db:SessionDep,clinic_id:UUID|None=None,product_key:str|None=None,date_from:date|None=None,date_to:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),_:PlatformOperator=Depends(require_platform_permission("platform.usage.read"))):
    cond=[]
    if clinic_id:cond.append(UsageEvent.clinic_id==clinic_id)
    if product_key:cond.append(UsageEvent.product_key==product_key)
    if date_from:cond.append(UsageEvent.created_at>=datetime.combine(date_from,time.min,tzinfo=timezone.utc))
    if date_to:cond.append(UsageEvent.created_at<datetime.combine(date_to+timedelta(days=1),time.min,tzinfo=timezone.utc))
    day=func.date(UsageEvent.created_at)
    grouped=select(day.label("date"),UsageEvent.clinic_id,UsageEvent.product_key,UsageEvent.event_type,func.count().label("count")).where(*cond).group_by(day,UsageEvent.clinic_id,UsageEvent.product_key,UsageEvent.event_type).subquery()
    total=await db.scalar(select(func.count()).select_from(grouped)) or 0
    rows=(await db.execute(select(grouped).order_by(grouped.c.date.desc(),grouped.c.clinic_id,grouped.c.product_key,grouped.c.event_type).offset((page-1)*page_size).limit(page_size))).all()
    return {"data":[{"date":r.date.isoformat(),"clinic_id":r.clinic_id,"product_key":r.product_key,"event_type":r.event_type,"count":r.count} for r in rows],"meta":{"total":total,"page":page,"page_size":page_size}}

@router.get("/audit-logs", response_model=ResponseEnvelope[list[AuditLogOut]])
async def audit_logs(db:SessionDep,operator_id:UUID|None=None,organization_id:UUID|None=None,clinic_id:UUID|None=None,action:str|None=None,date_from:date|None=None,date_to:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),_:PlatformOperator=Depends(require_platform_permission("platform.audit.read"))):
    cond=[]
    if operator_id:cond.append(PlatformAuditLog.operator_id==operator_id)
    if organization_id:cond.append(PlatformAuditLog.organization_id==organization_id)
    if clinic_id:cond.append(PlatformAuditLog.clinic_id==clinic_id)
    if action:cond.append(PlatformAuditLog.action==action)
    if date_from:cond.append(PlatformAuditLog.created_at>=datetime.combine(date_from,time.min,tzinfo=timezone.utc))
    if date_to:cond.append(PlatformAuditLog.created_at<datetime.combine(date_to+timedelta(days=1),time.min,tzinfo=timezone.utc))
    total=await db.scalar(select(func.count(PlatformAuditLog.id)).where(*cond)) or 0
    rows=(await db.execute(select(PlatformAuditLog,PlatformOperator.name).outerjoin(PlatformOperator,PlatformOperator.id==PlatformAuditLog.operator_id).where(*cond).order_by(PlatformAuditLog.created_at.desc()).offset((page-1)*page_size).limit(page_size))).all()
    data=[]
    for a,oname in rows:
        target_name=await _target_name(db,a)
        data.append({"id":a.id,"operator_id":a.operator_id,"operator_name":oname,"action":a.action,"target_type":a.target_type,"target_id":a.target_id,"target_name":target_name,"organization_id":a.organization_id,"clinic_id":a.clinic_id,"reason":a.reason,"ip":a.ip,"user_agent":a.user_agent,"details":a.details,"created_at":a.created_at})
    return {"data":data,"meta":{"total":total,"page":page,"page_size":page_size}}

@router.get("/operators", response_model=ResponseEnvelope[list[OperatorOut]])
async def operators(db:SessionDep,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),_:PlatformOperator=Depends(require_platform_permission("platform.operators.manage"))):
    total=await db.scalar(select(func.count(PlatformOperator.id))) or 0
    rows=(await db.scalars(select(PlatformOperator).order_by(PlatformOperator.created_at).offset((page-1)*page_size).limit(page_size))).all()
    return {"data":[{"id":o.id,"email":o.email,"name":o.name,"role":o.role,"is_active":o.is_active,"mfa_enabled":o.mfa_enabled,"last_login_at":o.last_login_at,"created_at":o.created_at,"updated_at":o.updated_at} for o in rows],"meta":{"total":total,"page":page,"page_size":page_size}}

@router.get("/overview", response_model=ResponseEnvelope[OverviewOut])
async def overview(db:SessionDep,_:PlatformOperator=Depends(require_platform_permission("platform.usage.read"))):
    organizations_total=await db.scalar(select(func.count(Organization.id))) or 0
    organizations_active=await db.scalar(select(func.count(Organization.id)).where(Organization.status=="active")) or 0
    organizations_suspended=await db.scalar(select(func.count(Organization.id)).where(Organization.status=="suspended")) or 0
    by_type={}
    for typ,count in (await db.execute(select(Organization.type,func.count()).group_by(Organization.type))).all(): by_type[typ]=count
    for typ in ("individual","clinic","chain","franchise","hospital","government","partner_platform"): by_type.setdefault(typ,0)
    clinics_total=await db.scalar(select(func.count(Clinic.id))) or 0
    clinics_active=await db.scalar(select(func.count(Clinic.id)).where(Clinic.status=="active")) or 0
    clinics_suspended=await db.scalar(select(func.count(Clinic.id)).where(Clinic.status=="suspended")) or 0
    now=datetime.now(timezone.utc)
    await ensure_canonical_products(db)
    await db.flush()
    product_counts=dict((await db.execute(select(WorkspaceProduct.product_id,func.count(func.distinct(WorkspaceProduct.clinic_id))).where(active_entitlement_clause(now)).group_by(WorkspaceProduct.product_id))).all())
    catalog=(await db.scalars(select(Product).where(Product.is_active.is_(True),Product.id!="clinical-decision-support").order_by(Product.name))).all()
    product_data=[{"product_key":product.id,"effective_clinics":product_counts.get(product.id,0)} for product in catalog]
    usage_count=await db.scalar(select(func.count(UsageEvent.id)).where(UsageEvent.created_at>=now-timedelta(days=30))) or 0
    recent=(await db.execute(select(PlatformAuditLog,PlatformOperator.name).outerjoin(PlatformOperator,PlatformOperator.id==PlatformAuditLog.operator_id).order_by(PlatformAuditLog.created_at.desc()).limit(10))).all()
    recent_audit=[]
    for a,name in recent:
        recent_audit.append({"id":a.id,"operator_id":a.operator_id,"operator_name":name,"action":a.action,"target_type":a.target_type,"target_id":a.target_id,"target_name":await _target_name(db,a),"organization_id":a.organization_id,"clinic_id":a.clinic_id,"reason":a.reason,"ip":a.ip,"user_agent":a.user_agent,"details":a.details,"created_at":a.created_at})
    return {"data":{"organizations":{"total":organizations_total,"active":organizations_active,"suspended":organizations_suspended,"by_type":by_type},"clinics":{"total":clinics_total,"active":clinics_active,"suspended":clinics_suspended},"products":product_data,"usage_last_30_days":usage_count,"recent_audit":recent_audit},"meta":{}}
