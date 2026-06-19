"""extend_schema

Revision ID: 17720d35ae64
Revises: 22021104ec07
Create Date: 2026-06-12 11:44:09.577012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17720d35ae64'
down_revision: Union[str, Sequence[str], None] = '22021104ec07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to posture_sessions
    op.add_column('posture_sessions', sa.Column('overall_confidence', sa.Float(), nullable=True))
    op.add_column('posture_sessions', sa.Column('annotated_front_image', sa.String(length=1024), nullable=True))
    op.add_column('posture_sessions', sa.Column('annotated_back_image', sa.String(length=1024), nullable=True))
    op.add_column('posture_sessions', sa.Column('annotated_side_image', sa.String(length=1024), nullable=True))

    # Add columns to posture_measurements
    op.add_column('posture_measurements', sa.Column('severity', sa.String(length=50), nullable=True))
    op.add_column('posture_measurements', sa.Column('visibility', sa.String(length=50), nullable=True))

    # Add columns to prescription_items
    op.add_column('prescription_items', sa.Column('note', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from prescription_items
    op.drop_column('prescription_items', 'note')

    # Remove columns from posture_measurements
    op.drop_column('posture_measurements', 'visibility')
    op.drop_column('posture_measurements', 'severity')

    # Remove columns from posture_sessions
    op.drop_column('posture_sessions', 'annotated_side_image')
    op.drop_column('posture_sessions', 'annotated_back_image')
    op.drop_column('posture_sessions', 'annotated_front_image')
    op.drop_column('posture_sessions', 'overall_confidence')

