"""Indexes for the prescription and appointment hot lists (BE fixes).

Pipeline report section E4: `prescriptions` had no index except the primary
key, and `prescription_items` none on prescription_id, so every list and every
item load was a sequential scan that grows with the data. Appointments lists
filter by clinic and a date range, so one composite index replaces the
planner's clinic filter on top of the scheduled_at index.

Index-only change: no column, no data change. Down drops exactly these five.

Revision ID: be1fixes20261124
Revises: pos1report20261123
"""
from alembic import op

revision = "be1fixes20261124"
down_revision = "pos1report20261123"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_prescriptions_clinic_created", "prescriptions", ["clinic_id", "created_at"])
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])
    op.create_index("ix_prescriptions_physio_id", "prescriptions", ["physio_id"])
    op.create_index("ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"])
    op.create_index("ix_appointments_clinic_scheduled", "appointments", ["clinic_id", "scheduled_at"])


def downgrade():
    op.drop_index("ix_appointments_clinic_scheduled", table_name="appointments")
    op.drop_index("ix_prescription_items_prescription_id", table_name="prescription_items")
    op.drop_index("ix_prescriptions_physio_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_patient_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_clinic_created", table_name="prescriptions")
