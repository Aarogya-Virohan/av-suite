"""Clinic setup from one YAML file (launch-plan EN-4).

    cd backend
    python -m scripts.clinic_setup path/to/clinic.yaml --staging --dry-run
    python -m scripts.clinic_setup path/to/clinic.yaml --staging

What it does, in order, and only what differs from the database (idempotent):
  1. organization block: skipped with a message until organizations exist on
     dev (Sparsh S1).
  2. clinic (looked up by slug): created with its first admin as owner
     (same code path as sign-up), then name / logo / address / contact
     fields set through PATCH /settings/clinic.
  3. tools: workspace_products rows enabled for the listed products and
     disabled for any other product the clinic has. CRM is always on.
  4. users: missing users created through POST /users (generated password,
     written to a 0600 credentials file, never printed). An email that already
     belongs to another clinic is skipped with a warning (audit AUD-01: never
     attach another clinic's account). Existing passwords are never changed.
  5. access: for therapist / front desk users, the capability set
     (role preset + tool checkboxes + explicit overrides) is written through
     PUT /users/{id}/permissions when it differs. Admins keep the admin
     template.

Writes go through the real API in-process (validation, audit log), except
workspace_products, which has no clinic-side route while the marketplace is
off (they are set by SQL today); that write gets its own audit row.

Safety: see scripts/safety.py. --staging: non-production env and a local DB
or the confirmed staging fingerprint. --production (real clinics, CL-1):
needs --confirm-db with the exact fingerprint "user@host/db" of the target.
The demo seed has no production mode.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.safety import guard_or_exit  # noqa: E402

ROLES = ("admin", "therapist", "front_desk")
CLINIC_FIELDS = (
    "name",
    "branding_color",
    "client_type",
    "address_line",
    "city",
    "state",
    "pincode",
    "phone",
    "email",
    "registration_number",
    "gstin",
    "authorised_person",
)
LOGO_MAX_BYTES = 2 * 1024 * 1024  # same cap as report_letterhead.LOGO_MAX_BYTES
LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}

# Role presets for non-admin users. Admins use the admin role template.
# Scopes: "all", "own" ("none" is the default for anything not listed).
PRESETS: dict[str, dict[str, str]] = {
    "therapist": {
        "patients.view": "all",
        "patients.create": "all",
        "patients.edit": "all",
        "leads.view": "all",
        "appointments.view": "all",
        "appointments.create": "all",
        "appointments.edit": "own",
        "treatments.view": "all",
        "treatments.create": "all",
        "treatments.edit": "own",
        "assessments.view": "all",
        "assessments.create": "all",
        "assessments.edit": "own",
        "documents.view": "all",
        "documents.upload": "all",
        "analytics.my_performance": "own",
    },
    "front_desk": {
        "patients.view": "all",
        "patients.create": "all",
        "patients.edit": "all",
        "leads.view": "all",
        "leads.create": "all",
        "leads.edit": "all",
        "leads.convert": "all",
        "appointments.view": "all",
        "appointments.create": "all",
        "appointments.edit": "all",
        "appointments.delete": "all",
        "invoices.view": "all",
        "invoices.create": "all",
        "payments.view": "all",
        "payments.record": "all",
        "packages.view": "all",
        "packages.assign": "all",
        "booking.view": "all",
        "booking.approve": "all",
        "booking.edit": "all",
        "documents.view": "all",
        "documents.upload": "all",
    },
    "none": {},
}

# The three tool checkboxes on a user (launch-plan BE-1 / CRM-6).
TOOL_CAPABILITIES: dict[str, dict[str, str]] = {
    "exercise-library": {
        "exercises.view": "all",
        "prescriptions.view": "all",
        "prescriptions.create": "all",
        "prescriptions.edit": "own",
    },
    "posture-tool": {"posture.view": "all", "posture.create": "all"},
    "psycho-social-screening": {
        "screening.assign": "all",
        "screening.view": "own",
        "screening.refer": "own",
    },
}
# A user tool needs these clinic products enabled.
TOOL_PRODUCTS: dict[str, tuple[str, ...]] = {
    "exercise-library": ("exercise-library", "exercise-prescription"),
    "posture-tool": ("posture-tool",),
    "psycho-social-screening": ("psycho-social-screening",),
}


class ConfigError(ValueError):
    pass


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
@dataclass
class UserSpec:
    email: str
    first_name: str
    last_name: str
    role: str
    phone: str | None = None
    preset: str | None = None
    tools: list[str] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)

    def desired_permissions(self) -> dict[str, str]:
        if self.role == "admin":
            return {}
        merged: dict[str, str] = dict(PRESETS[self.preset or self.role])
        for tool in self.tools:
            merged.update(TOOL_CAPABILITIES[tool])
        merged.update(self.permissions)
        return {k: v for k, v in merged.items() if v != "none"}


@dataclass
class SetupConfig:
    slug: str
    clinic: dict[str, Any]
    logo: str | None
    tools: list[str]
    users: list[UserSpec]
    organization: dict[str, Any] | None
    base_dir: Path

    @property
    def owner(self) -> UserSpec:
        return next(u for u in self.users if u.role == "admin")


def _require_str(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}.{key} is required (non-empty text).")
    return value.strip()


def parse_config(raw: dict[str, Any], base_dir: Path) -> SetupConfig:
    from app.core.products import CANONICAL_PRODUCTS
    from app.core.rbac import CAPABILITY_REGISTRY, validate_capability_scope

    if not isinstance(raw, dict):
        raise ConfigError("top level must be a mapping.")
    unknown = set(raw) - {"organization", "clinic", "tools", "users"}
    if unknown:
        raise ConfigError(f"unknown top-level keys: {sorted(unknown)}")

    clinic = raw.get("clinic") or {}
    if not isinstance(clinic, dict):
        raise ConfigError("clinic must be a mapping.")
    slug = _require_str(clinic, "slug", "clinic").lower()
    if not all(c.isalnum() or c == "-" for c in slug) or len(slug) > 120:
        raise ConfigError("clinic.slug: lowercase letters, digits and '-' only, max 120.")
    _require_str(clinic, "name", "clinic")
    bad = set(clinic) - set(CLINIC_FIELDS) - {"slug", "logo"}
    if bad:
        raise ConfigError(f"clinic: unknown keys {sorted(bad)}")
    clinic_fields = {k: clinic[k] for k in CLINIC_FIELDS if clinic.get(k) not in (None, "")}
    for key, value in clinic_fields.items():
        if not isinstance(value, str):
            clinic_fields[key] = str(value)

    product_ids = {p["id"] for p in CANONICAL_PRODUCTS}
    tools = list(dict.fromkeys(["crm", *(raw.get("tools") or [])]))
    for tool in tools:
        if tool not in product_ids:
            raise ConfigError(f"tools: unknown product {tool!r}; known: {sorted(product_ids)}")

    users_raw = raw.get("users") or []
    if not isinstance(users_raw, list) or not users_raw:
        raise ConfigError("users: at least one user (an admin) is required.")
    users: list[UserSpec] = []
    seen: set[str] = set()
    for i, item in enumerate(users_raw):
        where = f"users[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where} must be a mapping.")
        bad = set(item) - {"email", "first_name", "last_name", "role", "phone", "preset", "tools", "permissions"}
        if bad:
            raise ConfigError(f"{where}: unknown keys {sorted(bad)}")
        email = _require_str(item, "email", where).lower()
        if "@" not in email:
            raise ConfigError(f"{where}.email is not an email.")
        if email in seen:
            raise ConfigError(f"{where}.email {email} appears twice.")
        seen.add(email)
        role = _require_str(item, "role", where)
        if role not in ROLES:
            raise ConfigError(f"{where}.role must be one of {ROLES}.")
        preset = item.get("preset")
        if preset is not None and preset not in PRESETS:
            raise ConfigError(f"{where}.preset must be one of {sorted(PRESETS)}.")
        user_tools = list(item.get("tools") or [])
        for tool in user_tools:
            if tool not in TOOL_CAPABILITIES:
                raise ConfigError(f"{where}.tools: {tool!r} not one of {sorted(TOOL_CAPABILITIES)}.")
            missing = [p for p in TOOL_PRODUCTS[tool] if p not in tools]
            if missing:
                raise ConfigError(f"{where}.tools: {tool} needs clinic tools {missing}.")
        perms = item.get("permissions") or {}
        if not isinstance(perms, dict):
            raise ConfigError(f"{where}.permissions must be a mapping capability: scope.")
        for key, scope in perms.items():
            if key not in CAPABILITY_REGISTRY:
                raise ConfigError(f"{where}.permissions: unknown capability {key!r}.")
            try:
                validate_capability_scope(key, scope)
            except ValueError as exc:
                raise ConfigError(f"{where}.permissions: {exc}") from exc
        if role == "admin" and (preset or user_tools or perms):
            raise ConfigError(f"{where}: admins use the admin template; drop preset/tools/permissions.")
        users.append(
            UserSpec(
                email=email,
                first_name=_require_str(item, "first_name", where),
                last_name=_require_str(item, "last_name", where),
                role=role,
                phone=(str(item["phone"]) if item.get("phone") else None),
                preset=preset,
                tools=user_tools,
                permissions={k: str(v) for k, v in perms.items()},
            )
        )
    if not any(u.role == "admin" for u in users):
        raise ConfigError("users: at least one admin is required (the first admin owns the clinic).")

    org = raw.get("organization")
    if org is not None and not isinstance(org, dict):
        raise ConfigError("organization must be a mapping.")

    return SetupConfig(
        slug=slug,
        clinic=clinic_fields,
        logo=(str(clinic["logo"]).strip() if clinic.get("logo") else None),
        tools=tools,
        users=users,
        organization=org,
        base_dir=base_dir,
    )


def load_config(path: Path) -> SetupConfig:
    import yaml

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return parse_config(raw, path.resolve().parent)


def logo_data_url(spec: str, base_dir: Path) -> str:
    """https URL is kept as is; a file becomes a data URL like the settings page."""
    if spec.startswith("https://") or spec.startswith("data:image/"):
        return spec
    path = (base_dir / spec).resolve() if not os.path.isabs(spec) else Path(spec)
    if not path.is_file():
        raise ConfigError(f"clinic.logo: file not found: {path}")
    data = path.read_bytes()
    if len(data) > LOGO_MAX_BYTES:
        raise ConfigError(f"clinic.logo: {len(data)} bytes, max {LOGO_MAX_BYTES}.")
    mime = mimetypes.guess_type(path.name)[0] or ""
    if mime not in LOGO_TYPES:
        raise ConfigError(f"clinic.logo: {mime or 'unknown type'}; use PNG, JPEG or WebP.")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


# --------------------------------------------------------------------------
# In-process API
# --------------------------------------------------------------------------
class Api:
    """Calls the FastAPI app in-process with a token minted for one user."""

    def __init__(self, user_id, clinic_id, role: str) -> None:
        import httpx

        from app.core.security import create_access_token
        from app.main import app

        token = create_access_token(subject=str(user_id), clinic_id=str(clinic_id), role=role)
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://setup.local/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )

    async def __aenter__(self) -> "Api":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def call(self, method: str, path: str, expect: tuple[int, ...] = (200, 201), **kw) -> Any:
        resp = await self._client.request(method, path, **kw)
        if resp.status_code not in expect:
            raise RuntimeError(f"{method} {path} -> {resp.status_code}: {resp.text[:500]}")
        if not resp.content:
            return None
        body = resp.json()
        if isinstance(body, dict) and "data" in body and set(body) <= {"data", "meta"}:
            return body["data"]
        return body


# --------------------------------------------------------------------------
# Plan + apply
# --------------------------------------------------------------------------
@dataclass
class Result:
    clinic_id: Any = None
    owner_id: Any = None
    user_ids: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    new_credentials: dict[str, str] = field(default_factory=dict)


def _say(result: Result, line: str) -> None:
    result.actions.append(line)
    print(line)


async def _organizations_table_exists(session) -> bool:
    from sqlalchemy import text

    found = await session.scalar(text("select to_regclass('public.organizations') is not null"))
    return bool(found)


async def apply_config(
    cfg: SetupConfig,
    *,
    dry_run: bool,
    password_for: Any = None,
) -> Result:
    """Bring the database in line with cfg. password_for(email) -> str | None."""

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.enums.product import EntitlementSource, EntitlementStatus
    from app.enums.user import UserRole
    from app.models.clinic import Clinic
    from app.models.membership import Membership
    from app.models.product import WorkspaceProduct
    from app.models.user import User
    from app.models.user_permission import UserPermission
    from app.schemas.auth import RegisterRequest
    from app.services.audit import log_event_safely
    from app.services.auth_service import register_user
    from app.services.product_entitlements import ensure_canonical_products

    result = Result()
    tag = "[dry-run] " if dry_run else ""
    gen = password_for or (lambda _email: None)

    async with AsyncSessionLocal() as db:
        # 1. organization
        if cfg.organization is not None:
            if await _organizations_table_exists(db):
                _say(result, f"{tag}organization: table exists (S1 merged) but this script does not write organizations yet; skipped.")
            else:
                _say(result, f"{tag}organization: skipped, organizations are not on dev yet (Sparsh S1). Clinic is set up on its own.")

        # 2. clinic
        clinic = await db.scalar(select(Clinic).where(Clinic.slug == cfg.slug))
        owner_spec = cfg.owner
        if clinic is None:
            other = await db.scalar(select(User).where(User.email == owner_spec.email))
            if other is not None:
                raise ConfigError(
                    f"owner {owner_spec.email} already has an account in another clinic;"
                    " use a new email for the first admin."
                )
            _say(result, f"{tag}clinic {cfg.slug}: create '{cfg.clinic['name']}' with owner {owner_spec.email}")
            if dry_run:
                result.actions.append("(dry-run stops here for a new clinic: nothing else exists to diff)")
                for u in cfg.users:
                    _say(result, f"{tag}user {u.email}: create as {u.role}")
                _say(result, f"{tag}tools: enable {cfg.tools}")
                return result
            password = gen(owner_spec.email) or secrets.token_urlsafe(12)
            await register_user(
                db,
                RegisterRequest(
                    clinic_name=cfg.clinic["name"],
                    email=owner_spec.email,
                    password=password,
                    first_name=owner_spec.first_name,
                    last_name=owner_spec.last_name,
                ),
            )
            result.new_credentials[owner_spec.email] = password
            owner = await db.scalar(select(User).where(User.email == owner_spec.email))
            clinic = await db.get(Clinic, owner.clinic_id)
            clinic.slug = cfg.slug
            await db.commit()
        else:
            _say(result, f"clinic {cfg.slug}: exists ({clinic.id})")

        clinic_id = clinic.id
        result.clinic_id = clinic_id

        # Acting admin: the owner if present, else any active admin member.
        owner = await db.scalar(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.clinic_id == clinic_id, Membership.role == UserRole.ADMIN, User.is_active.is_(True))
            .order_by((User.email == owner_spec.email).desc(), User.created_at)
        )
        if owner is None:
            raise ConfigError(f"clinic {cfg.slug} has no active admin to act as.")
        result.owner_id = owner.id

        # 2b. clinic fields
        desired = dict(cfg.clinic)
        if cfg.logo:
            desired["branding_logo_url"] = logo_data_url(cfg.logo, cfg.base_dir)
        changes = {
            k: v for k, v in desired.items() if (getattr(clinic, k, None) or None) != (v or None)
        }

        # 3. tools (workspace_products)
        await ensure_canonical_products(db)
        rows = {
            r.product_id: r
            for r in (await db.scalars(select(WorkspaceProduct).where(WorkspaceProduct.clinic_id == clinic_id))).all()
        }
        tool_changes: list[tuple[str, str, str]] = []
        for product_id in cfg.tools:
            row = rows.get(product_id)
            before = row.status.value if row else "none"
            if before != EntitlementStatus.ENABLED.value:
                tool_changes.append((product_id, before, "enabled"))
        for product_id, row in rows.items():
            if product_id not in cfg.tools and row.status == EntitlementStatus.ENABLED:
                tool_changes.append((product_id, "enabled", "disabled"))
        for product_id, before, after in tool_changes:
            _say(result, f"{tag}tool {product_id}: {before} -> {after}")
        if not tool_changes:
            _say(result, f"tools: unchanged {sorted(cfg.tools)}")
        if not dry_run and tool_changes:
            for product_id, before, after in tool_changes:
                row = rows.get(product_id)
                if row is None:
                    row = WorkspaceProduct(
                        clinic_id=clinic_id,
                        product_id=product_id,
                        status=EntitlementStatus(after),
                        source=EntitlementSource.DIRECT,
                    )
                    db.add(row)
                else:
                    row.status = EntitlementStatus(after)
                await log_event_safely(
                    db, clinic_id, owner.id, "update", "workspace_product", None,
                    {"product_id": product_id, "before": {"status": before},
                     "after": {"status": after}, "via": "scripts/clinic_setup.py"},
                )
            await db.commit()
        else:
            await db.rollback()

        # 4 + 5. users and access: read state first
        members = {
            u.email.lower(): (u, m)
            for u, m in (
                await db.execute(
                    select(User, Membership)
                    .join(Membership, Membership.user_id == User.id)
                    .where(Membership.clinic_id == clinic_id)
                )
            ).all()
        }
        existing_users = {
            u.email.lower(): u
            for u in (
                await db.scalars(select(User).where(User.email.in_([s.email for s in cfg.users])))
            ).all()
        }
        perm_rows: dict[Any, dict[str, str]] = {}
        for p in (await db.scalars(select(UserPermission).where(UserPermission.clinic_id == clinic_id))).all():
            perm_rows.setdefault(p.user_id, {})[p.capability_key] = p.scope.value

    if changes:
        shown = {k: ("<logo>" if k == "branding_logo_url" else v) for k, v in changes.items()}
        _say(result, f"{tag}clinic fields: {shown}")
    else:
        _say(result, "clinic fields: unchanged")

    if dry_run:
        for spec in cfg.users:
            if spec.email in members:
                user, membership = members[spec.email]
                if membership.role.value != spec.role:
                    _say(result, f"WARNING user {spec.email}: role is {membership.role.value}, YAML says {spec.role}; role changes are not done by this script.")
                want = spec.desired_permissions()
                have = {k: v for k, v in perm_rows.get(user.id, {}).items() if v != "none"}
                if spec.role != "admin" and want != have:
                    _say(result, f"{tag}user {spec.email}: permissions {len(have)} -> {len(want)} keys")
                else:
                    _say(result, f"user {spec.email}: unchanged")
            elif spec.email in existing_users:
                _say(result, f"WARNING user {spec.email}: account belongs to another clinic; skipped (AUD-01).")
            else:
                _say(result, f"{tag}user {spec.email}: create as {spec.role}")
        return result

    async with Api(owner.id, clinic_id, "admin") as api:
        if changes:
            await api.call("PATCH", "/settings/clinic", json=changes)

        for spec in cfg.users:
            if spec.email in members:
                user, membership = members[spec.email]
                if membership.role.value != spec.role:
                    _say(result, f"WARNING user {spec.email}: role is {membership.role.value}, YAML says {spec.role}; role changes are not done by this script.")
                user_id = user.id
            elif spec.email in existing_users:
                # POST /users would attach another clinic's account (AUD-01). Never do that.
                _say(result, f"WARNING user {spec.email}: account belongs to another clinic; skipped (AUD-01).")
                continue
            else:
                password = gen(spec.email) or secrets.token_urlsafe(12)
                created = await api.call(
                    "POST",
                    "/users",
                    json={
                        "email": spec.email,
                        "role": spec.role,
                        "password": password,
                        "first_name": spec.first_name,
                        "last_name": spec.last_name,
                        "phone": spec.phone,
                    },
                )
                user_id = created["id"]
                result.new_credentials[spec.email] = password
                _say(result, f"user {spec.email}: created as {spec.role}")
            result.user_ids[spec.email] = user_id

            if spec.role == "admin":
                continue
            want = spec.desired_permissions()
            have = {
                k: v for k, v in perm_rows.get(_uuid(user_id), {}).items() if v != "none"
            }
            if want == have:
                _say(result, f"user {spec.email}: permissions unchanged ({len(want)} keys)")
                continue
            await api.call(
                "PUT",
                f"/users/{user_id}/permissions",
                json=[{"capability_key": k, "scope": v} for k, v in sorted(want.items())],
            )
            _say(result, f"user {spec.email}: permissions set ({len(have)} -> {len(want)} keys)")

    result.user_ids.setdefault(owner_spec.email, owner.id)
    return result


def _uuid(value):
    import uuid

    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def write_credentials(path: Path, slug: str, creds: dict[str, str]) -> None:
    if not creds:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        for email, password in creds.items():
            fh.write(f"{slug}\t{email}\t{password}\n")
    os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("config", type=Path, help="clinic YAML")
    parser.add_argument("--staging", action="store_true", help="required: confirms a staging or local database")
    parser.add_argument(
        "--production",
        action="store_true",
        help="real clinic on prod (CL-1): needs --confirm-db <user@host/db> of the target; always --dry-run first",
    )
    parser.add_argument("--confirm-db", default="", help="exact fingerprint printed by a --dry-run, for --production")
    parser.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    parser.add_argument(
        "--credentials-out",
        type=Path,
        default=Path.home() / ".av-setup" / "credentials.tsv",
        help="where passwords of NEW users are appended (0600). Default ~/.av-setup/credentials.tsv",
    )
    args = parser.parse_args(argv)

    target = guard_or_exit(
        staging_flag=args.staging,
        production_confirm=(args.confirm_db if args.production else None),
    )
    print(f"target database: {target.fingerprint}" + ("  [PRODUCTION]" if args.production else ""))

    import asyncio

    try:
        cfg = load_config(args.config)
        result = asyncio.run(apply_config(cfg, dry_run=args.dry_run))
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 1
    if result.new_credentials:
        write_credentials(args.credentials_out, cfg.slug, result.new_credentials)
        print(f"{len(result.new_credentials)} new login(s); passwords written to {args.credentials_out}")
    print("dry run: nothing written." if args.dry_run else "done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
