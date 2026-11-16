"""exercise templates

Revision ID: a3d8f1c5e7b2
Revises: f4a9c2e7b1d3
Create Date: 2026-10-30

Tables for exercise templates (EL-D-009): a saved program of exercises with
default dose that fills a new prescription. clinic_id NULL is reserved for AV
templates shared with every clinic; this release only lets a clinic make its
own.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a3d8f1c5e7b2"
down_revision: Union[str, Sequence[str], None] = "f4a9c2e7b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercise_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exercise_templates_clinic_id", "exercise_templates", ["clinic_id"])

    op.create_table(
        "exercise_template_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("exercise_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sets", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reps", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("hold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("frequency", sa.String(100), nullable=False, server_default="Daily"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("template_id", "exercise_id", name="uq_exercise_template_items_template_exercise"),
    )
    op.create_index("ix_exercise_template_items_template_id", "exercise_template_items", ["template_id"])
    op.create_index("ix_exercise_template_items_exercise_id", "exercise_template_items", ["exercise_id"])


def downgrade() -> None:
    op.drop_index("ix_exercise_template_items_exercise_id", table_name="exercise_template_items")
    op.drop_index("ix_exercise_template_items_template_id", table_name="exercise_template_items")
    op.drop_table("exercise_template_items")
    op.drop_index("ix_exercise_templates_clinic_id", table_name="exercise_templates")
    op.drop_table("exercise_templates")
