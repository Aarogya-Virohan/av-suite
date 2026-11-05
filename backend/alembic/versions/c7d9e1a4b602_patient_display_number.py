"""Add clinic-scoped patient display numbers and backfill existing patients.

Revision ID: c7d9e1a4b602
Revises: f2b6c8d0a134
"""
from alembic import op
import sqlalchemy as sa


revision = "c7d9e1a4b602"
down_revision = "f2b6c8d0a134"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_counters",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("last_number", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("clinic_id"),
    )
    op.add_column("patients", sa.Column("display_number", sa.BigInteger(), nullable=True))
    op.execute(sa.text("""
        WITH numbered AS (
            SELECT id, row_number() OVER (
                PARTITION BY clinic_id ORDER BY created_at ASC, id ASC
            ) AS assigned_number
            FROM patients
        )
        UPDATE patients AS patient
        SET display_number = numbered.assigned_number
        FROM numbered
        WHERE patient.id = numbered.id
    """))
    op.execute(sa.text("""
        INSERT INTO patient_counters (clinic_id, last_number)
        SELECT clinic_id, MAX(display_number)
        FROM patients
        GROUP BY clinic_id
    """))
    op.create_unique_constraint(
        "uq_patients_clinic_display_number", "patients", ["clinic_id", "display_number"]
    )
    op.alter_column("patients", "display_number", nullable=False)


def downgrade() -> None:
    op.drop_constraint("uq_patients_clinic_display_number", "patients", type_="unique")
    op.drop_column("patients", "display_number")
    op.drop_table("patient_counters")
