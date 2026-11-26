"""Branding (Round 4) clinic fields + D-043 document numbers (27 Nov 2026).

clinics: display_doctor_name and website (both optional) and logo_bg_mode
(as_is | white | transparent, default as_is; every existing clinic gets
as_is, which is how its logo looked before apart from the old automatic
background removal).

document_counters: one generic counter per clinic, document type and period
(RX / POS / PSY never reset, period ""; INV / RCP per Indian financial year,
period "2627").

Number columns: prescriptions.number, posture_sessions.number,
payments.receipt_number and the new psychosocial_reports table (one row and
PSY number per psychosocial PDF export), each unique per clinic.

Backfill: every existing prescription and every saved posture report gets
<clinic code>-RX|POS-<6 digits> in created_at order per clinic, and the
counters start after the last one. Invoices keep the numbers they were issued
with (INV-0001 style); new invoices get INV-<FY>-<6 digits>. Payments made
before this keep no receipt number, so their receipt still shows the invoice
number it showed before.

Downgrade drops everything added here; no other data is touched.

Revision ID: brnum20261127
Revises: crm10code20261124
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "brnum20261127"
down_revision = "crm10code20261124"
branch_labels = None
depends_on = None


def _backfill(table: str, doc_type: str, where: str) -> None:
    op.execute(
        f"""
        WITH ordered AS (
            SELECT t.id,
                   c.code,
                   row_number() OVER (PARTITION BY t.clinic_id ORDER BY t.created_at ASC, t.id ASC) AS n
            FROM {table} t
            JOIN clinics c ON c.id = t.clinic_id
            WHERE {where}
        )
        UPDATE {table} t
        SET number = ordered.code || '-{doc_type}-' || lpad(ordered.n::text, 6, '0')
        FROM ordered
        WHERE ordered.id = t.id
        """
    )
    op.execute(
        f"""
        INSERT INTO document_counters (clinic_id, doc_type, period, last_number)
        SELECT clinic_id, '{doc_type}', '', count(*)
        FROM {table}
        WHERE number IS NOT NULL
        GROUP BY clinic_id
        """
    )


def upgrade() -> None:
    op.add_column("clinics", sa.Column("display_doctor_name", sa.String(length=255), nullable=True))
    op.add_column("clinics", sa.Column("website", sa.String(length=255), nullable=True))
    op.add_column(
        "clinics",
        sa.Column("logo_bg_mode", sa.String(length=12), nullable=False, server_default="as_is"),
    )
    op.create_check_constraint(
        "ck_clinics_logo_bg_mode", "clinics", "logo_bg_mode IN ('as_is', 'white', 'transparent')"
    )

    op.create_table(
        "document_counters",
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.String(length=8), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("clinic_id", "doc_type", "period", name="pk_document_counters"),
    )

    op.create_table(
        "psychosocial_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=24), nullable=False),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("clinic_id", "number", name="uq_psychosocial_reports_clinic_number"),
    )
    op.create_index(
        "ix_psychosocial_reports_clinic_patient", "psychosocial_reports", ["clinic_id", "patient_id"]
    )

    op.add_column("prescriptions", sa.Column("number", sa.String(length=24), nullable=True))
    op.add_column("posture_sessions", sa.Column("number", sa.String(length=24), nullable=True))
    op.add_column("payments", sa.Column("receipt_number", sa.String(length=16), nullable=True))

    _backfill("prescriptions", "RX", "TRUE")
    _backfill("posture_sessions", "POS", "t.report_json IS NOT NULL")

    op.create_unique_constraint("uq_prescriptions_clinic_number", "prescriptions", ["clinic_id", "number"])
    op.create_unique_constraint(
        "uq_posture_sessions_clinic_number", "posture_sessions", ["clinic_id", "number"]
    )
    op.create_unique_constraint(
        "uq_payments_clinic_receipt_number", "payments", ["clinic_id", "receipt_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_payments_clinic_receipt_number", "payments", type_="unique")
    op.drop_constraint("uq_posture_sessions_clinic_number", "posture_sessions", type_="unique")
    op.drop_constraint("uq_prescriptions_clinic_number", "prescriptions", type_="unique")
    op.drop_column("payments", "receipt_number")
    op.drop_column("posture_sessions", "number")
    op.drop_column("prescriptions", "number")
    op.drop_index("ix_psychosocial_reports_clinic_patient", table_name="psychosocial_reports")
    op.drop_table("psychosocial_reports")
    op.drop_table("document_counters")
    op.drop_constraint("ck_clinics_logo_bg_mode", "clinics", type_="check")
    op.drop_column("clinics", "logo_bg_mode")
    op.drop_column("clinics", "website")
    op.drop_column("clinics", "display_doctor_name")
