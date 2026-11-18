"""Tool 03 referral contact directory

Revision ID: e7a1c4b9d2f6
Revises: d5f9b3c7e2a4
Create Date: 2026-10-22

The clinic's list of people and services it refers patients to (SRS 4.3.1).
Contacts are archived, never deleted. A referral action can name one: it
keeps a link to the contact plus a copy of the name and role at that time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "e7a1c4b9d2f6"
down_revision: Union[str, Sequence[str], None] = "d5f9b3c7e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept identical to app/models/psychosocial.py on purpose: a migration must
# not import app code that can change after it ships.
CONTACT_NAME_MAX = 120
CONTACT_ROLE_MAX = 80
CONTACT_PHONE_MAX = 32
CONTACT_EMAIL_MAX = 254
CONTACT_NOTE_MAX = 500


def upgrade() -> None:
    op.create_table(
        "psychosocial_referral_contacts",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(CONTACT_NAME_MAX), nullable=False),
        sa.Column("role", sa.String(CONTACT_ROLE_MAX), nullable=False),
        sa.Column("phone", sa.String(CONTACT_PHONE_MAX), nullable=True),
        sa.Column("email", sa.String(CONTACT_EMAIL_MAX), nullable=True),
        sa.Column("note", sa.String(CONTACT_NOTE_MAX), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("phone IS NOT NULL OR email IS NOT NULL", name="ck_psy_contact_reachable"),
    )
    op.create_index("ix_psy_contacts_clinic", "psychosocial_referral_contacts", ["clinic_id"])

    op.add_column(
        "psychosocial_referral_actions",
        sa.Column(
            "contact_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey(
                "psychosocial_referral_contacts.id",
                ondelete="SET NULL",
                name="fk_psy_referral_actions_contact_id",
            ),
            nullable=True,
        ),
    )
    op.add_column("psychosocial_referral_actions", sa.Column("contact_name", sa.String(CONTACT_NAME_MAX), nullable=True))
    op.add_column("psychosocial_referral_actions", sa.Column("contact_role", sa.String(CONTACT_ROLE_MAX), nullable=True))


def downgrade() -> None:
    op.drop_column("psychosocial_referral_actions", "contact_role")
    op.drop_column("psychosocial_referral_actions", "contact_name")
    op.drop_constraint("fk_psy_referral_actions_contact_id", "psychosocial_referral_actions", type_="foreignkey")
    op.drop_column("psychosocial_referral_actions", "contact_id")
    op.drop_index("ix_psy_contacts_clinic", table_name="psychosocial_referral_contacts")
    op.drop_table("psychosocial_referral_contacts")
