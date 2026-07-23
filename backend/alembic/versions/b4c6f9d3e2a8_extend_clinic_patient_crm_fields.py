"""extend_clinic_patient_crm_fields

Revision ID: b4c6f9d3e2a8
Revises: a3f5e8c2d1b7
Create Date: 2026-07-23

Adds CRM-specific columns to the existing clinics and patients tables.
Additive only — no existing column is altered or dropped.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4c6f9d3e2a8'
down_revision = 'a3f5e8c2d1b7'
branch_labels = None
depends_on = None

clinicplantier = sa.Enum('free', 'practice', 'clinical_pro', name='clinicplantier')
patientstatus = sa.Enum('active', 'inactive', 'discharged', name='patientstatus')


def upgrade() -> None:
    bind = op.get_bind()
    clinicplantier.create(bind, checkfirst=True)
    patientstatus.create(bind, checkfirst=True)

    op.add_column('clinics', sa.Column('branding_logo_url', sa.String(length=2048), nullable=True))
    op.add_column('clinics', sa.Column('branding_color', sa.String(length=32), nullable=True))
    op.add_column('clinics', sa.Column(
        'plan_tier', clinicplantier, nullable=False, server_default='free'
    ))
    op.add_column('clinics', sa.Column(
        'is_partner_clinic', sa.Boolean(), nullable=False, server_default=sa.false()
    ))

    op.add_column('patients', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('patients', sa.Column('gender', sa.String(length=32), nullable=True))
    op.add_column('patients', sa.Column('chief_complaint', sa.Text(), nullable=True))
    op.add_column('patients', sa.Column('referral_source', sa.String(length=255), nullable=True))
    op.add_column('patients', sa.Column(
        'status', patientstatus, nullable=False, server_default='active'
    ))
    op.add_column('patients', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'deleted_at')
    op.drop_column('patients', 'status')
    op.drop_column('patients', 'referral_source')
    op.drop_column('patients', 'chief_complaint')
    op.drop_column('patients', 'gender')
    op.drop_column('patients', 'age')

    op.drop_column('clinics', 'is_partner_clinic')
    op.drop_column('clinics', 'plan_tier')
    op.drop_column('clinics', 'branding_color')
    op.drop_column('clinics', 'branding_logo_url')

    patientstatus.drop(op.get_bind(), checkfirst=True)
    clinicplantier.drop(op.get_bind(), checkfirst=True)
