"""crm_schema_v2_consolidate_all_changes

Revision ID: e9f1a2b3c4d5
Revises: c5d8e9f4a1b2
Create Date: 2026-08-08

Consolidates all post-CRM schema decisions into a single migration:
  - therapist_id + finalized flags on soap_assessments & treatment_sessions
  - date_of_birth on patients and appointment_requests (age KEPT; computed on read)
  - appointment_type on appointments
  - payment_status ENUM + status + idempotency_key on payments
  - gender_type, specialty_type, lead_source_type ENUMs (VARCHAR columns KEPT)
  - pain_score CHECK constraint on treatment_sessions
  - Tightened users.role CHECK to remove 'patient'

ADDITIVE RULE COMPLIANCE NOTE:
  age, user_id, VARCHAR gender/specialty/source columns are KEPT in the DB.
  We add new columns alongside them. Application layer validates via Python enum.
  Dropping old columns is deferred to a later migration once app no longer reads them.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers
revision: str = 'e9f1a2b3c4d5'
down_revision: Union[str, None] = 'c5d8e9f4a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ──────────────────────────────────────────────────────────────
    # 1. soap_assessments — add therapist_id (nullable) + finalized
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE soap_assessments ADD COLUMN IF NOT EXISTS therapist_id UUID REFERENCES users(id)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_soap_assessments_therapist_id ON soap_assessments(therapist_id)")
        op.execute("ALTER TABLE soap_assessments ADD COLUMN IF NOT EXISTS finalized BOOLEAN NOT NULL DEFAULT false")
    else:
        with op.batch_alter_table('soap_assessments') as batch_op:
            batch_op.add_column(sa.Column('therapist_id', PGUUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
            batch_op.add_column(sa.Column('finalized', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # ──────────────────────────────────────────────────────────────
    # 2. treatment_sessions — add finalized flag
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE treatment_sessions ADD COLUMN IF NOT EXISTS finalized BOOLEAN NOT NULL DEFAULT false")
    else:
        with op.batch_alter_table('treatment_sessions') as batch_op:
            batch_op.add_column(sa.Column('finalized', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # ──────────────────────────────────────────────────────────────
    # 3. patients — add date_of_birth (age column KEPT for now)
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS date_of_birth DATE")
    else:
        with op.batch_alter_table('patients') as batch_op:
            batch_op.add_column(sa.Column('date_of_birth', sa.Date(), nullable=True))

    # ──────────────────────────────────────────────────────────────
    # 4. appointment_requests — add date_of_birth (age KEPT for now)
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE appointment_requests ADD COLUMN IF NOT EXISTS date_of_birth DATE")
    else:
        with op.batch_alter_table('appointment_requests') as batch_op:
            batch_op.add_column(sa.Column('date_of_birth', sa.Date(), nullable=True))

    # ──────────────────────────────────────────────────────────────
    # 5. appointments — add appointment_type
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS appointment_type VARCHAR(100) NOT NULL DEFAULT 'consultation'")
    else:
        with op.batch_alter_table('appointments') as batch_op:
            batch_op.add_column(sa.Column('appointment_type', sa.String(length=100), nullable=False, server_default='consultation'))

    # ──────────────────────────────────────────────────────────────
    # 6. payments — add status ENUM + idempotency_key
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'voided', 'refunded'); END IF; END $$;")
        op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS status payment_status NOT NULL DEFAULT 'completed'")
        op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255)")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_payments_idempotency_key') THEN ALTER TABLE payments ADD CONSTRAINT uq_payments_idempotency_key UNIQUE (idempotency_key); END IF; END $$;")
    else:
        with op.batch_alter_table('payments') as batch_op:
            batch_op.add_column(sa.Column('status', sa.String(50), server_default='completed', nullable=False))
            batch_op.add_column(sa.Column('idempotency_key', sa.String(255), nullable=True))

    # ──────────────────────────────────────────────────────────────
    # 7. New ENUMs: gender_type, specialty_type, lead_source_type
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gender_type') THEN CREATE TYPE gender_type AS ENUM ('male', 'female', 'other'); END IF; END $$;")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'specialty_type') THEN CREATE TYPE specialty_type AS ENUM ('physiotherapy', 'chiropractic', 'osteopathy', 'massage', 'acupuncture', 'other'); END IF; END $$;")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_source_type') THEN CREATE TYPE lead_source_type AS ENUM ('website', 'referral', 'social_media', 'walk_in', 'advertisement', 'other'); END IF; END $$;")

    # ──────────────────────────────────────────────────────────────
    # 8. pain_score CHECK constraint on treatment_sessions
    # ──────────────────────────────────────────────────────────────
    if bind.dialect.name == 'postgresql':
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_treatment_sessions_pain_score') THEN ALTER TABLE treatment_sessions ADD CONSTRAINT ck_treatment_sessions_pain_score CHECK (pain_score >= 0 AND pain_score <= 10); END IF; END $$;")
    else:
        op.create_check_constraint('ck_treatment_sessions_pain_score', 'treatment_sessions', 'pain_score >= 0 AND pain_score <= 10')

    # ──────────────────────────────────────────────────────────────
    # 9. users.role — tighten CHECK to remove 'patient'
    # ──────────────────────────────────────────────────────────────
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('admin', 'therapist', 'front_desk')"
    )


def downgrade() -> None:
    bind = op.get_bind()

    # 9. Restore users.role CHECK
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('admin', 'therapist', 'front_desk', 'patient')"
    )

    # 8. Remove pain_score CHECK
    op.drop_constraint('ck_treatment_sessions_pain_score',
                       'treatment_sessions', type_='check')

    # 7. Drop ENUMs
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS gender_type')
        op.execute('DROP TYPE IF EXISTS specialty_type')
        op.execute('DROP TYPE IF EXISTS lead_source_type')

    # 6. payments
    op.drop_constraint('uq_payments_idempotency_key', 'payments', type_='unique')
    op.drop_column('payments', 'idempotency_key')
    op.drop_column('payments', 'status')
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS payment_status')

    # 5. appointments
    op.drop_column('appointments', 'appointment_type')

    # 4. appointment_requests
    op.drop_column('appointment_requests', 'date_of_birth')

    # 3. patients
    op.drop_column('patients', 'date_of_birth')

    # 2. treatment_sessions
    op.drop_column('treatment_sessions', 'finalized')

    # 1. soap_assessments
    op.drop_column('soap_assessments', 'finalized')
    op.drop_index('ix_soap_assessments_therapist_id',
                  table_name='soap_assessments')
    op.drop_column('soap_assessments', 'therapist_id')
