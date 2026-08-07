"""add_therapist_id_and_finalized_fields

Revision ID: d6e7f8a9b0c1
Revises: c5d8e9f4a1b2
Create Date: 2026-08-07

Adds therapist_id and finalized boolean flag to soap_assessments,
and finalized boolean flag to treatment_sessions.
Additive only migration with safe server_default / nullable columns.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5d8e9f4a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add therapist_id to soap_assessments (nullable=True for backward compatibility)
    op.add_column(
        'soap_assessments',
        sa.Column('therapist_id', PGUUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
    )
    op.create_index(
        'ix_soap_assessments_therapist_id',
        'soap_assessments',
        ['therapist_id']
    )

    # 2. Add finalized boolean flag to soap_assessments (default false)
    op.add_column(
        'soap_assessments',
        sa.Column('finalized', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )

    # 3. Add finalized boolean flag to treatment_sessions (default false)
    op.add_column(
        'treatment_sessions',
        sa.Column('finalized', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('treatment_sessions', 'finalized')
    op.drop_column('soap_assessments', 'finalized')
    op.drop_index('ix_soap_assessments_therapist_id', table_name='soap_assessments')
    op.drop_column('soap_assessments', 'therapist_id')
