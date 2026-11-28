import uuid
import re
import unicodedata
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from sqlalchemy import String, Enum, Boolean, Text, event, CheckConstraint, ForeignKey, Index, UniqueConstraint, select
from app.enums.clinic import ClinicPlanTier, ClinicType
from app.enums.organization import ClinicStatus
from app.models.base import Base, TimestampMixin


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"
    __table_args__ = (
        CheckConstraint("client_type IN ('clinic', 'hospital', 'home_care')", name="ck_clinics_client_type"),
        CheckConstraint("status IN ('active', 'suspended')", name="ck_clinics_status"),
        CheckConstraint("length(code) BETWEEN 1 AND 6", name="ck_clinics_code_length"),
        CheckConstraint(
            "logo_bg_mode IN ('as_is', 'white', 'transparent')", name="ck_clinics_logo_bg_mode"
        ),
        UniqueConstraint("code", name="uq_clinics_code"),
        Index("ix_clinics_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # Prefix of the Patient ID (ADP-000003). Set automatically on insert from
    # the name when not given; the clinic admin can change it in Settings.
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ClinicStatus.ACTIVE,
        server_default=ClinicStatus.ACTIVE.value,
    )
    type: Mapped[ClinicType] = mapped_column(
        Enum(
            ClinicType,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            name="clinic_type",
            length=20,
        ),
        nullable=False,
        default=ClinicType.CLINIC,
    )
    branding_logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_type: Mapped[str] = mapped_column(String(20), nullable=False, default="clinic")
    branding_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    authorised_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Round 4 branding (26 Nov 2026). Doctor name in the clinical report header
    # (empty = clinic owner admin's name), website in the clinic block above the
    # footer, and how the logo background is shown on the band (BR-b).
    display_doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_bg_mode: Mapped[str] = mapped_column(
        String(12), nullable=False, default="as_is", server_default="as_is"
    )
    plan_tier: Mapped[ClinicPlanTier] = mapped_column(
        Enum(
            ClinicPlanTier,
            values_callable=lambda e: [member.value for member in e],
            name="clinicplantier",
        ),
        nullable=False,
        default=ClinicPlanTier.FREE,
    )
    is_partner_clinic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_documents_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    users = relationship("User", back_populates="clinic", foreign_keys="User.clinic_id")
    organization = relationship("Organization", back_populates="clinics")
    memberships = relationship(
        "Membership", back_populates="clinic", cascade="all, delete-orphan"
    )
    patients = relationship("Patient", back_populates="clinic")
    exercises = relationship("Exercise", back_populates="clinic")
    prescriptions = relationship("Prescription", back_populates="clinic")
    posture_sessions = relationship("PostureSession", back_populates="clinic")
    user_permissions = relationship(
        "UserPermission", back_populates="clinic", cascade="all, delete-orphan"
    )
    workspace_products = relationship(
        "WorkspaceProduct", back_populates="clinic", cascade="all, delete-orphan"
    )


@event.listens_for(Clinic, "init")
def _set_default_clinic_slug(target, args, kwargs) -> None:
    """Give newly constructed clinics a stable, unique public slug by default."""
    if kwargs.get("slug"):
        return
    clinic_id = kwargs.get("id") or uuid.uuid4()
    kwargs.setdefault("id", clinic_id)
    name = kwargs.get("name", "clinic")
    normalized = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "clinic"
    kwargs["slug"] = f"{base[:107].rstrip('-')}-{str(clinic_id).replace('-', '')[:12]}"


@event.listens_for(Clinic, "before_insert")
def _set_default_clinic_code(mapper, connection, target) -> None:
    """A clinic created without a code gets the one derived from its name, or
    that with a number added if another clinic already uses it."""
    if target.code:
        return
    from app.services.clinic_code import derive_clinic_code, next_free_code

    base = derive_clinic_code(target.name)
    rows = connection.execute(select(Clinic.code).where(Clinic.code.like(f"{base[:5]}%")))
    taken = {r[0] for r in rows}
    # Clinics added in the same flush are not in the table yet.
    session = object_session(target)
    if session is not None:
        taken |= {c.code for c in session.new if isinstance(c, Clinic) and c.code}
    target.code = next_free_code(base, taken)
