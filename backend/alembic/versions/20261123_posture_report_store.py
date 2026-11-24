"""Store posture reports in posture_sessions (POS-2 / BE-2).

Until now POST /posture/report wrote the report to data/reports on the
container disk, which Railway wipes on every deploy. These columns let a
posture_sessions row (already tied to clinic_id and patient_id) carry the
report id and the saved report JSON, so a report can be re-opened and
downloaded again. All columns are nullable: rows made before this revision
have no report.

Revision ID: pos1report20261123
Revises: s3usage20261122
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "pos1report20261123"
down_revision = "s3usage20261122"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posture_sessions", sa.Column("report_id", sa.String(40), nullable=True))
    op.add_column("posture_sessions", sa.Column("report_json", postgresql.JSONB(), nullable=True))
    op.add_column("posture_sessions", sa.Column("analysis_version", sa.String(40), nullable=True))
    op.add_column(
        "posture_sessions",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_posture_sessions_report_id", "posture_sessions", ["report_id"], unique=True)
    op.create_index("ix_posture_sessions_clinic_patient_created", "posture_sessions", ["clinic_id", "patient_id", "created_at"])


def downgrade():
    op.drop_index("ix_posture_sessions_clinic_patient_created", table_name="posture_sessions")
    op.drop_index("ix_posture_sessions_report_id", table_name="posture_sessions")
    op.drop_column("posture_sessions", "created_by_user_id")
    op.drop_column("posture_sessions", "analysis_version")
    op.drop_column("posture_sessions", "report_json")
    op.drop_column("posture_sessions", "report_id")
