"""seed_demo_login_data

Revision ID: d8a9f0c1b2e3
Revises: c5d8e9f4a1b2
Create Date: 2026-08-03

Seeds deterministic demo data for CRM login testing.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8a9f0c1b2e3"
down_revision: Union[str, Sequence[str], None] = "c5d8e9f4a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEMO_CLINIC_ID = "11111111-1111-1111-1111-111111111111"
DEMO_THERAPIST_ID = "33333333-3333-3333-3333-333333333333"
DEMO_PATIENT_1_ID = "44444444-4444-4444-4444-444444444444"
DEMO_PATIENT_2_ID = "55555555-5555-5555-5555-555555555555"
DEMO_PASSWORD_HASH = "$2b$12$9Ls0tgrLvXrXNjea/D/90e6G86RKAKi42oYT/ySAS71sGh1Dq/zhe"


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO clinics (
                id, name, branding_color, plan_tier, is_partner_clinic
            )
            VALUES (
                :clinic_id, 'Aarogya Virohan Demo Clinic',
                '#008080', 'clinical_pro', true
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                branding_color = EXCLUDED.branding_color,
                plan_tier = EXCLUDED.plan_tier,
                is_partner_clinic = EXCLUDED.is_partner_clinic
            """
        ),
        {"clinic_id": DEMO_CLINIC_ID},
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO users (
                id, clinic_id, email, password_hash, role,
                first_name, last_name, phone, is_active
            )
            VALUES
                (
                    '22222222-2222-2222-2222-222222222222',
                    :clinic_id, 'admin@avtest.com', :password_hash,
                    'admin', 'Admin', 'User', '9876543211', true
                ),
                (
                    '66666666-6666-6666-6666-666666666666',
                    :clinic_id, 'frontdesk@avtest.com', :password_hash,
                    'front_desk', 'Front', 'Desk', '9876543212', true
                ),
                (
                    :therapist_id,
                    :clinic_id, 'therapist@avtest.com', :password_hash,
                    'therapist', 'Main', 'Therapist', '9876543213', true
                )
            ON CONFLICT (email) DO UPDATE SET
                clinic_id = EXCLUDED.clinic_id,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                phone = EXCLUDED.phone,
                is_active = EXCLUDED.is_active
            """
        ),
        {
            "clinic_id": DEMO_CLINIC_ID,
            "therapist_id": DEMO_THERAPIST_ID,
            "password_hash": DEMO_PASSWORD_HASH,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO leads (
                id, clinic_id, name, phone, source, stage
            )
            VALUES (
                '77777777-7777-7777-7777-777777777777',
                :clinic_id, 'John Prospect', '9000000001',
                'Facebook', 'new'
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"clinic_id": DEMO_CLINIC_ID},
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO patients (
                id, clinic_id, first_name, last_name, phone,
                age, gender, chief_complaint, status
            )
            VALUES
                (
                    :patient_1_id, :clinic_id, 'Alice', 'Patient',
                    '9000000002', 30, 'Female', 'Lower back pain', 'active'
                ),
                (
                    :patient_2_id, :clinic_id, 'Bob', 'Patient',
                    '9000000003', 45, 'Male', 'Shoulder injury', 'active'
                )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "clinic_id": DEMO_CLINIC_ID,
            "patient_1_id": DEMO_PATIENT_1_ID,
            "patient_2_id": DEMO_PATIENT_2_ID,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO appointments (
                id, clinic_id, patient_id, therapist_id,
                scheduled_at, duration_minutes, status, source
            )
            VALUES
                (
                    '88888888-8888-8888-8888-888888888888',
                    :clinic_id, :patient_1_id, :therapist_id,
                    now() + interval '1 day' + interval '10 hours',
                    45, 'scheduled', 'manual'
                ),
                (
                    '99999999-9999-9999-9999-999999999999',
                    :clinic_id, :patient_2_id, :therapist_id,
                    now() + interval '1 day' + interval '14 hours',
                    30, 'scheduled', 'manual'
                )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "clinic_id": DEMO_CLINIC_ID,
            "patient_1_id": DEMO_PATIENT_1_ID,
            "patient_2_id": DEMO_PATIENT_2_ID,
            "therapist_id": DEMO_THERAPIST_ID,
        },
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM clinics WHERE id = :clinic_id").bindparams(
            clinic_id=DEMO_CLINIC_ID
        )
    )
