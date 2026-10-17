from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine, text


def load_backfill_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "a8c4e2f1d903_backfill_missing_memberships.py"
    )
    spec = importlib.util.spec_from_file_location("membership_backfill_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_migration_preserves_rows_and_skips_existing_memberships(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users "
                "(id TEXT PRIMARY KEY, clinic_id TEXT NULL, role TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE memberships "
                "(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, clinic_id TEXT NOT NULL, "
                "role TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
                "UNIQUE(user_id, clinic_id))"
            )
        )

        missing_id, existing_id, no_clinic_id = (str(uuid.uuid4()) for _ in range(3))
        clinic_a, clinic_b = str(uuid.uuid4()), str(uuid.uuid4())
        connection.execute(
            text(
                "INSERT INTO users (id, clinic_id, role) VALUES "
                "(:missing_id, :clinic_a, 'therapist'), "
                "(:existing_id, :clinic_a, 'admin'), "
                "(:no_clinic_id, NULL, 'front_desk')"
            ),
            {
                "missing_id": missing_id,
                "existing_id": existing_id,
                "no_clinic_id": no_clinic_id,
                "clinic_a": clinic_a,
            },
        )
        connection.execute(
            text(
                "INSERT INTO memberships "
                "(id, user_id, clinic_id, role, created_at, updated_at) "
                "VALUES (:id, :user_id, :clinic_id, 'front_desk', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": existing_id,
                "clinic_id": clinic_b,
            },
        )

        migration = load_backfill_migration()
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

        def bulk_insert(table, rows):
            for row in rows:
                connection.execute(
                    text(
                        "INSERT INTO memberships "
                        "(id, user_id, clinic_id, role, created_at, updated_at) "
                        "VALUES (:id, :user_id, :clinic_id, :role, :created_at, :updated_at)"
                    ),
                    {
                        **{key: str(value) for key, value in row.items() if key in {"id", "user_id", "clinic_id", "role"}},
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                    },
                )

        monkeypatch.setattr(migration.op, "bulk_insert", bulk_insert)
        migration.upgrade()
        migration.upgrade()

        inserted = connection.execute(
            text("SELECT clinic_id, role FROM memberships WHERE user_id = :id"),
            {"id": missing_id},
        ).one()
        assert inserted.clinic_id == clinic_a
        assert inserted.role == "therapist"
        assert connection.execute(
            text("SELECT COUNT(*) FROM memberships WHERE user_id = :id"),
            {"id": missing_id},
        ).scalar_one() == 1
        preserved = connection.execute(
            text("SELECT clinic_id, role FROM memberships WHERE user_id = :id"),
            {"id": existing_id},
        ).one()
        assert (preserved.clinic_id, preserved.role) == (clinic_b, "front_desk")
        assert connection.execute(
            text("SELECT COUNT(*) FROM memberships WHERE user_id = :id"),
            {"id": no_clinic_id},
        ).scalar_one() == 0
    engine.dispose()
