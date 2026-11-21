"""Add platform operators and append-only audit logs.

Revision ID: s2plat20261120
Revises: s1fnd20261120
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s2plat20261120"
down_revision = "s1fnd20261120"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_operators",
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("mfa_secret", sa.Text(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_totp_step", sa.Integer(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'support')", name="ck_platform_operators_role"),
    )
    op.create_index("ix_platform_operators_email", "platform_operators", ["email"], unique=True)
    op.create_table(
        "platform_audit_logs",
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["platform_operators.id"], name="fk_platform_audit_logs_operator_id_platform_operators"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_platform_audit_logs_organization_id_organizations"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_platform_audit_logs_clinic_id_clinics"),
    )
    op.create_index("ix_platform_audit_logs_created_at", "platform_audit_logs", ["created_at"])
    op.create_index("ix_platform_audit_logs_organization_id", "platform_audit_logs", ["organization_id"])
    op.create_index("ix_platform_audit_logs_operator_id", "platform_audit_logs", ["operator_id"])
    op.create_table(
        "platform_auth_rate_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_platform_auth_rate_limits_updated_at", "platform_auth_rate_limits", ["updated_at"])


def downgrade():
    op.drop_index("ix_platform_auth_rate_limits_updated_at", table_name="platform_auth_rate_limits")
    op.drop_table("platform_auth_rate_limits")
    op.drop_index("ix_platform_audit_logs_operator_id", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_logs_organization_id", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_logs_created_at", table_name="platform_audit_logs")
    op.drop_table("platform_audit_logs")
    op.drop_index("ix_platform_operators_email", table_name="platform_operators")
    op.drop_table("platform_operators")
