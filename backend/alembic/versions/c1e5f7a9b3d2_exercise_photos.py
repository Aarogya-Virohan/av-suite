"""exercise photos: a clinic's own front and side photos of an exercise

Revision ID: c1e5f7a9b3d2
Revises: a8c4e2f1d903
Create Date: 2026-10-27

Note: the open CDSS branch (feat/tool03-psychosocial) also chains from
a8c4e2f1d903. Whichever of the two reaches dev second must point its first
migration's down_revision at the other branch's last revision and be tested
again, so dev keeps a single head.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "c1e5f7a9b3d2"
down_revision: Union[str, Sequence[str], None] = "a8c4e2f1d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercise_photos",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", PGUUID(as_uuid=True), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("angle", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("clinic_id", "exercise_id", "angle", name="uq_exercise_photos_clinic_exercise_angle"),
        sa.CheckConstraint("angle IN ('front', 'side')", name="ck_exercise_photos_angle"),
    )
    op.create_index("ix_exercise_photos_clinic_id", "exercise_photos", ["clinic_id"])
    op.create_index("ix_exercise_photos_exercise_id", "exercise_photos", ["exercise_id"])


def downgrade() -> None:
    op.drop_index("ix_exercise_photos_exercise_id", table_name="exercise_photos")
    op.drop_index("ix_exercise_photos_clinic_id", table_name="exercise_photos")
    op.drop_table("exercise_photos")
