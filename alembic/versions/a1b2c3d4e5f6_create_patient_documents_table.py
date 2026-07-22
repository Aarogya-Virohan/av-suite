"""create patient documents table

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-07-22 21:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

document_category = postgresql.ENUM(
    "medical_report", "prescription", "lab_result", "consent_form", "x_ray_scan", "id_proof", "other",
    name="document_category",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(
        "medical_report", "prescription", "lab_result", "consent_form", "x_ray_scan", "id_proof", "other",
        name="document_category",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("treatment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("category", document_category, nullable=False, server_default="other"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatment_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_documents_clinic_id", "patient_documents", ["clinic_id"], unique=False)
    op.create_index("ix_patient_documents_patient_id", "patient_documents", ["patient_id"], unique=False)
    op.create_index("ix_patient_documents_treatment_id", "patient_documents", ["treatment_id"], unique=False)
    op.create_index("ix_patient_documents_uploaded_by", "patient_documents", ["uploaded_by"], unique=False)
    op.create_index("ix_patient_documents_category", "patient_documents", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patient_documents_category", table_name="patient_documents")
    op.drop_index("ix_patient_documents_uploaded_by", table_name="patient_documents")
    op.drop_index("ix_patient_documents_treatment_id", table_name="patient_documents")
    op.drop_index("ix_patient_documents_patient_id", table_name="patient_documents")
    op.drop_index("ix_patient_documents_clinic_id", table_name="patient_documents")
    op.drop_table("patient_documents")
    postgresql.ENUM(name="document_category").drop(op.get_bind(), checkfirst=True)
