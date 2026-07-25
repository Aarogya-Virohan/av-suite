"""convert_user_role_to_varchar_check

Revision ID: c5d8e9f4a1b2
Revises: b4c6f9d3e2a8
Create Date: 2026-07-25

Converts User.role from PostgreSQL native enum to VARCHAR + CHECK.
Updates legacy role 'physio' to canonical 'therapist'.
Provides complete upgrade and downgrade path.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c5d8e9f4a1b2"
down_revision = "2bfb0d5801d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Convert the role column type to VARCHAR(50)
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(50) USING role::text")
    else:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("role", type_=sa.String(length=50))

    # 2. Update legacy 'physio' role values to 'therapist'
    op.execute("UPDATE users SET role = 'therapist' WHERE role = 'physio'")

    # 3. Add CHECK constraint on users table
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'therapist', 'front_desk', 'patient')"
    )

    # 4. Cleanup PostgreSQL native enum type if it exists
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Remove CHECK constraint
    op.drop_constraint("ck_users_role", "users", type_="check")

    # 2. Convert 'therapist' back to 'physio'
    op.execute("UPDATE users SET role = 'physio' WHERE role = 'therapist'")

    # 3. Restore PostgreSQL native enum behavior if PostgreSQL
    if bind.dialect.name == "postgresql":
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN CREATE TYPE userrole AS ENUM ('admin', 'physio', 'patient', 'front_desk'); END IF; END $$;")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
    else:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("role", type_=sa.Enum("admin", "physio", "patient", "front_desk", name="userrole"))
