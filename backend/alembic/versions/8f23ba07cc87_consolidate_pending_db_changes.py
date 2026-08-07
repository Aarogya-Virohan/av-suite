"""consolidate_pending_db_changes

Revision ID: 8f23ba07cc87
Revises: d6e7f8a9b0c1
Create Date: 2026-08-07 21:07:08.600042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f23ba07cc87'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. patients table
    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_constraint("patients_user_id_fkey", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("age")
    
    # 2. appointment_requests table
    with op.batch_alter_table("appointment_requests") as batch_op:
        batch_op.drop_column("age")
        batch_op.add_column(sa.Column("date_of_birth", sa.Date(), nullable=True))
    
    # 3. appointments table
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.add_column(sa.Column("appointment_type", sa.String(length=100), server_default="consultation", nullable=False))
    
    # 4. payments table
    if bind.dialect.name == "postgresql":
        op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'voided', 'refunded')")
        op.execute("ALTER TABLE payments ADD COLUMN status payment_status NOT NULL DEFAULT 'completed'")
    else:
        with op.batch_alter_table("payments") as batch_op:
            batch_op.add_column(sa.Column("status", sa.String(length=50), server_default="completed", nullable=False))
            
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_payments_idempotency_key", ["idempotency_key"])

    # 5. users table (role constraint)
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'therapist', 'front_desk')"
    )


def downgrade() -> None:
    bind = op.get_bind()

    # 1. users table
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'therapist', 'front_desk', 'patient')"
    )

    # 2. payments table
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("uq_payments_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("status")
        
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS payment_status")

    # 3. appointments table
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.drop_column("appointment_type")

    # 4. appointment_requests table
    with op.batch_alter_table("appointment_requests") as batch_op:
        batch_op.drop_column("date_of_birth")
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))

    # 5. patients table
    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key("patients_user_id_fkey", "users", ["user_id"], ["id"], ondelete="SET NULL")
