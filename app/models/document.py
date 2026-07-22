from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base
from app.common.mixins import TimestampMixin, UUIDMixin
from app.enums.document import DocumentCategory
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.treatment import TreatmentSession
from app.models.user import User


def _document_category_values(enum_cls: type[DocumentCategory]) -> list[str]:
    """Return database enum values for document category."""

    return [member.value for member in enum_cls]


class PatientDocument(UUIDMixin, TimestampMixin, Base):
    """Patient document and medical file metadata entity."""

    __tablename__: str = "patient_documents"
    __table_args__: tuple[Index, ...] = (
        Index("ix_patient_documents_clinic_id", "clinic_id"),
        Index("ix_patient_documents_patient_id", "patient_id"),
        Index("ix_patient_documents_treatment_id", "treatment_id"),
        Index("ix_patient_documents_uploaded_by", "uploaded_by"),
        Index("ix_patient_documents_category", "category"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    patient: Mapped[Patient] = relationship()

    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    uploader: Mapped[User | None] = relationship()

    treatment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("treatment_sessions.id"),
        nullable=True,
    )
    treatment: Mapped[TreatmentSession | None] = relationship()

    file_url: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(length=100), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    label: Mapped[str] = mapped_column(String(length=255), nullable=False)
    category: Mapped[DocumentCategory] = mapped_column(
        Enum(
            DocumentCategory,
            name="document_category",
            values_callable=_document_category_values,
            create_type=False,
        ),
        default=DocumentCategory.OTHER,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
