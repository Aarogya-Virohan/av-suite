"""Guard rails shared by the demo seed (tests/seed.py) and the clinic setup
script (scripts/clinic_setup.py).

Both scripts write rows. They must never run against production by accident,
so every run passes ALL of these checks before any app module (and so any
database engine) is imported:

1. The caller passed --staging explicitly.
2. ENVIRONMENT (and RAILWAY_ENVIRONMENT_NAME when present) is not production.
3. The database is either local (localhost / 127.0.0.1 / ::1 / unix socket /
   local sqlite file) or a remote database whose fingerprint "user@host/db"
   - is NOT listed in PROD_DB_FINGERPRINTS below or in the env var
     AV_PROD_DB_FINGERPRINTS (comma separated), and
   - equals AV_STAGING_DB_FINGERPRINT exactly (the operator types the
     staging fingerprint once, so a copied prod URL cannot slip through).

Supabase poolers share one host per region (prod and staging can both be
aws-0-ap-southeast-1.pooler.supabase.com); the project ref lives in the user
name ("postgres.<ref>"), which is why the fingerprint includes the user.
A fingerprint never contains a password.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

# Known production databases, "user@host/db" (no passwords). A match is a hard
# stop even if every other check passes. Add the prod Supabase pooler user
# here (QUESTIONS FOR ONKAR, L0); AV_PROD_DB_FINGERPRINTS extends it at run time.
PROD_DB_FINGERPRINTS: frozenset[str] = frozenset()

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", ""})
PROD_ENV_NAMES = ("prod", "production", "live")


class UnsafeTarget(Exception):
    """A write script must not touch this database. Scripts exit with code 2."""

    def __str__(self) -> str:
        return f"REFUSED: {self.args[0]}"


def check_production_target(
    *, confirm: str | None, environ: dict[str, str] | None = None, database_url: str | None = None
) -> "DbTarget":
    """Production writes (clinic setup only, never the seed): the operator
    must type the exact fingerprint of the database being written."""

    env = dict(os.environ if environ is None else environ)
    target = parse_database_url(database_url or env.get("DATABASE_URL", ""))
    if not confirm:
        raise UnsafeTarget(f"--production needs --confirm-db {target.fingerprint}")
    if confirm.strip().lower() != target.fingerprint.lower():
        raise UnsafeTarget(f"--confirm-db {confirm} does not match the database {target.fingerprint}.")
    return target


def guard_or_exit(*, staging_flag: bool, production_confirm: str | None = None) -> "DbTarget":
    """check_target for script entry points: print the reason and exit 2."""
    import sys

    try:
        if production_confirm is not None:
            if staging_flag:
                raise UnsafeTarget("use either --staging or --production, not both.")
            return check_production_target(confirm=production_confirm)
        return check_target(staging_flag=staging_flag)
    except UnsafeTarget as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None


@dataclass(frozen=True)
class DbTarget:
    scheme: str
    user: str
    host: str
    database: str

    @property
    def fingerprint(self) -> str:
        return f"{self.user}@{self.host}/{self.database}"

    @property
    def is_local(self) -> bool:
        if self.scheme.startswith("sqlite"):
            # sqlite+aiosqlite:///./x.db has no host; //remote-host/x.db has one.
            return self.host == ""
        return self.host in LOCAL_HOSTS or self.host.startswith("/")


def parse_database_url(url: str) -> DbTarget:
    if not url:
        raise UnsafeTarget("DATABASE_URL is not set.")
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    user = unquote(parts.username or "")
    database = parts.path.lstrip("/")
    # postgresql://user@/db?host=/tmp (unix socket) keeps host in the query.
    if not host and "host=" in parts.query:
        for pair in parts.query.split("&"):
            if pair.startswith("host="):
                host = unquote(pair[5:]).lower()
    return DbTarget(scheme=parts.scheme.lower(), user=user, host=host, database=database)


def _is_prod_name(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in PROD_ENV_NAMES


def check_target(
    *,
    staging_flag: bool,
    environ: dict[str, str] | None = None,
    database_url: str | None = None,
    prod_fingerprints: frozenset[str] | None = None,
) -> DbTarget:
    """Return the DB target when it is safe to write, else raise UnsafeTarget."""

    env = dict(os.environ if environ is None else environ)
    if not staging_flag:
        raise UnsafeTarget(
            "pass --staging to confirm this is a staging or local database."
        )

    for key in ("ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT"):
        if _is_prod_name(env.get(key)):
            raise UnsafeTarget(f"{key}={env.get(key)!r} is production.")

    target = parse_database_url(database_url or env.get("DATABASE_URL", ""))

    blocked = set(PROD_DB_FINGERPRINTS if prod_fingerprints is None else prod_fingerprints)
    blocked |= {
        item.strip().lower()
        for item in env.get("AV_PROD_DB_FINGERPRINTS", "").split(",")
        if item.strip()
    }
    fingerprint = target.fingerprint.lower()
    # Match on the full fingerprint and on user@host alone (any database name).
    user_host = fingerprint.split("/", 1)[0]
    if fingerprint in blocked or user_host in {b.split("/", 1)[0] for b in blocked}:
        raise UnsafeTarget(f"{target.fingerprint} is a production database.")

    if target.is_local:
        return target

    confirmed = env.get("AV_STAGING_DB_FINGERPRINT", "").strip().lower()
    if not confirmed:
        raise UnsafeTarget(
            f"remote database {target.fingerprint}: set AV_STAGING_DB_FINGERPRINT"
            " to this exact value to confirm it is the staging database."
        )
    if confirmed != fingerprint:
        raise UnsafeTarget(
            f"remote database {target.fingerprint} does not match"
            f" AV_STAGING_DB_FINGERPRINT={confirmed}."
        )
    return target
