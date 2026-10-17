"""Reconcile global exercise seeds and payment status."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision = "c3a5f9d2e714"
down_revision = "0d063288208b"
branch_labels = None
depends_on = None


def _load_canonical_exercises() -> list[dict[str, object]]:
    seed_path = Path(__file__).with_name("22021104ec07_seed_exercises.py")
    spec = importlib.util.spec_from_file_location(
        "seed_exercises_22021104ec07", seed_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load canonical exercise payload: {seed_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SEED_EXERCISES


def _ensure_payment_status_type() -> None:
    op.execute(sa.text("""
            DO $$
            DECLARE existing_labels text[];
            BEGIN
                SELECT array_agg(e.enumlabel::text ORDER BY e.enumsortorder)
                INTO existing_labels
                FROM pg_type AS t
                JOIN pg_namespace AS n ON n.oid = t.typnamespace
                JOIN pg_enum AS e ON e.enumtypid = t.oid
                WHERE n.nspname = 'public'
                  AND t.typname = 'payment_status';

                IF existing_labels IS NULL THEN
                    CREATE TYPE public.payment_status AS ENUM (
                        'pending', 'completed', 'voided', 'refunded'
                    );
                ELSIF existing_labels IS DISTINCT FROM
                    ARRAY['pending', 'completed', 'voided', 'refunded']::text[] THEN
                    RAISE EXCEPTION
                        'public.payment_status has unexpected labels: %',
                        existing_labels;
                END IF;
            END
            $$;
            """))


def _restore_global_exercises() -> None:
    exercises = sa.table(
        "exercises",
        sa.column("id", sa.Uuid()),
        sa.column("clinic_id", sa.Uuid()),
        sa.column("title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("body_part", sa.String()),
        sa.column("is_free", sa.Boolean()),
        sa.column("video_url", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        schema="public",
    )
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": UUID(seed["id"]),
            "clinic_id": None,
            "title": seed["title"],
            "description": seed["description"],
            "body_part": seed["body_part"],
            "is_free": seed["is_free"],
            "video_url": seed["video_url"],
            "created_at": now,
            "updated_at": now,
        }
        for seed in _load_canonical_exercises()
    ]
    op.get_bind().execute(
        pg_insert(exercises)
        .values(rows)
        .on_conflict_do_nothing(index_elements=[exercises.c.id])
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("This reconciliation migration requires PostgreSQL.")

    _restore_global_exercises()
    _ensure_payment_status_type()

    op.execute(sa.text("""
            DO $$
            DECLARE existing_type text;
            BEGIN
                SELECT udt_schema || '.' || udt_name
                INTO existing_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'payments'
                  AND column_name = 'status';

                IF existing_type IS NOT NULL
                   AND existing_type <> 'public.payment_status' THEN
                    RAISE EXCEPTION
                        'public.payments.status has unexpected type: %',
                        existing_type;
                END IF;
            END
            $$;
            """))
    op.execute(
        sa.text(
            "ALTER TABLE public.payments "
            "ADD COLUMN IF NOT EXISTS status public.payment_status"
        )
    )
    op.execute(
        sa.text("UPDATE public.payments SET status = 'completed' WHERE status IS NULL")
    )
    op.execute(
        sa.text(
            "ALTER TABLE public.payments " "ALTER COLUMN status SET DEFAULT 'completed'"
        )
    )
    op.execute(sa.text("ALTER TABLE public.payments ALTER COLUMN status SET NOT NULL"))


def downgrade() -> None:
    raise RuntimeError(
        "This reconciliation is forward-only; downgrade would destroy restored data."
    )
