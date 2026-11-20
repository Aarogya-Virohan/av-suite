"""L0 enablers: safety guard, clinic setup config, presets (launch-plan EN-1, EN-4).

The full seed and setup runs against an Alembic-built Postgres are part of the
L0 test pack; these tests cover the rules that must never regress.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import clinic_setup
from scripts.safety import UnsafeTarget, check_production_target, check_target, parse_database_url

LOCAL = "postgresql+asyncpg://postgres@localhost:5433/l0"
POOLER = "aws-0-ap-southeast-1.pooler.supabase.com"
STAGING = f"postgresql+asyncpg://postgres.stagingref:secret@{POOLER}:5432/postgres"
PROD = f"postgresql+asyncpg://postgres.prodref:secret@{POOLER}:5432/postgres"


def env(**kw: str) -> dict[str, str]:
    return {"ENVIRONMENT": "staging", **kw}


# --------------------------------------------------------------------------
# safety
# --------------------------------------------------------------------------
def test_staging_flag_is_required():
    with pytest.raises(UnsafeTarget, match="--staging"):
        check_target(staging_flag=False, environ=env(), database_url=LOCAL)


@pytest.mark.parametrize(
    "key,value",
    [("ENVIRONMENT", "production"), ("ENVIRONMENT", "Prod"), ("RAILWAY_ENVIRONMENT_NAME", "production")],
)
def test_production_environment_is_refused(key, value):
    with pytest.raises(UnsafeTarget, match="production"):
        check_target(staging_flag=True, environ={key: value}, database_url=LOCAL)


@pytest.mark.parametrize(
    "url",
    [
        LOCAL,
        "postgresql+asyncpg://postgres@127.0.0.1/x",
        "postgresql+asyncpg://postgres@/x?host=/tmp",
        "sqlite+aiosqlite:///./test.db",
    ],
)
def test_local_databases_pass(url):
    assert check_target(staging_flag=True, environ=env(), database_url=url).is_local


def test_remote_needs_confirmed_fingerprint():
    with pytest.raises(UnsafeTarget, match="AV_STAGING_DB_FINGERPRINT"):
        check_target(staging_flag=True, environ=env(), database_url=STAGING)


def test_remote_with_other_fingerprint_is_refused():
    # Same pooler host, different project: a copied prod URL must not pass.
    with pytest.raises(UnsafeTarget, match="does not match"):
        check_target(
            staging_flag=True,
            environ=env(AV_STAGING_DB_FINGERPRINT=f"postgres.stagingref@{POOLER}/postgres"),
            database_url=PROD,
        )


def test_remote_with_matching_fingerprint_passes():
    target = check_target(
        staging_flag=True,
        environ=env(AV_STAGING_DB_FINGERPRINT=f"postgres.stagingref@{POOLER}/postgres"),
        database_url=STAGING,
    )
    assert target.fingerprint == f"postgres.stagingref@{POOLER}/postgres"
    assert "secret" not in target.fingerprint


def test_prod_fingerprint_is_a_hard_stop_even_when_confirmed():
    fp = f"postgres.prodref@{POOLER}/postgres"
    with pytest.raises(UnsafeTarget, match="production database"):
        check_target(
            staging_flag=True,
            environ=env(AV_STAGING_DB_FINGERPRINT=fp),
            database_url=PROD,
            prod_fingerprints=frozenset({fp}),
        )
    # user@host alone (any db name) also blocks, from the env list too.
    with pytest.raises(UnsafeTarget, match="production database"):
        check_target(
            staging_flag=True,
            environ=env(AV_STAGING_DB_FINGERPRINT=fp, AV_PROD_DB_FINGERPRINTS=f"postgres.prodref@{POOLER}"),
            database_url=PROD,
        )


def test_production_mode_needs_the_exact_fingerprint():
    fp = f"postgres.prodref@{POOLER}/postgres"
    with pytest.raises(UnsafeTarget, match="--confirm-db"):
        check_production_target(confirm="", environ={}, database_url=PROD)
    with pytest.raises(UnsafeTarget, match="does not match"):
        check_production_target(confirm=f"postgres.stagingref@{POOLER}/postgres", environ={}, database_url=PROD)
    assert check_production_target(confirm=fp.upper(), environ={}, database_url=PROD).fingerprint == fp


def test_setup_refuses_staging_and_production_together(capsys):
    with pytest.raises(SystemExit) as exc:
        clinic_setup.main(["x.yaml", "--staging", "--production", "--confirm-db", "a@b/c"])
    assert exc.value.code == 2
    assert "not both" in capsys.readouterr().err


def test_seed_has_no_production_mode():
    from tests import seed

    with pytest.raises(SystemExit):
        seed.main(["--staging", "--production"])


@pytest.mark.parametrize(
    "url",
    [
        f"postgresql+asyncpg://postgres.twijgohkslvkeqeyntkm:pw@{POOLER}:5432/postgres",
        "postgresql+asyncpg://postgres.twijgohkslvkeqeyntkm:pw@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        "postgresql+asyncpg://postgres:pw@db.twijgohkslvkeqeyntkm.supabase.co:5432/postgres",
    ],
)
def test_prod_supabase_ref_is_refused_on_any_host(url):
    target = parse_database_url(url)
    with pytest.raises(UnsafeTarget, match="production Supabase project"):
        check_target(
            staging_flag=True,
            environ=env(AV_STAGING_DB_FINGERPRINT=target.fingerprint),
            database_url=url,
        )


def test_remote_sqlite_is_not_local():
    assert not parse_database_url("sqlite+aiosqlite://remote-host/test.db").is_local


def test_script_entry_points_exit_2_without_staging(capsys):
    from tests import seed

    with pytest.raises(SystemExit) as exc:
        seed.main([])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        clinic_setup.main(["scripts/clinic.example.yaml"])
    assert exc.value.code == 2
    assert "REFUSED" in capsys.readouterr().err


# --------------------------------------------------------------------------
# presets and config
# --------------------------------------------------------------------------
def test_presets_and_tool_capabilities_are_valid():
    from app.core.rbac import validate_capability_scope

    for mapping in [*clinic_setup.PRESETS.values(), *clinic_setup.TOOL_CAPABILITIES.values()]:
        for key, scope in mapping.items():
            validate_capability_scope(key, scope)


def test_tool_capabilities_match_their_products():
    from app.core.products import product_for_capability

    for tool, caps in clinic_setup.TOOL_CAPABILITIES.items():
        for key in caps:
            assert product_for_capability(key) in clinic_setup.TOOL_PRODUCTS[tool], key


def test_example_yaml_parses():
    path = Path(clinic_setup.__file__).parent / "clinic.example.yaml"
    cfg = clinic_setup.load_config(path)
    assert cfg.slug == "example-physio-noida"
    assert cfg.owner.email == "owner@example-physio.in"
    assert cfg.tools[0] == "crm"
    therapist = cfg.users[1]
    assert therapist.desired_permissions()["posture.create"] == "all"
    assert cfg.users[2].desired_permissions()["invoices.edit"] == "all"


def base(**over):
    raw = {
        "clinic": {"slug": "t-clinic", "name": "T"},
        "tools": ["exercise-library", "exercise-prescription"],
        "users": [{"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"}],
    }
    raw.update(over)
    return raw


@pytest.mark.parametrize(
    "raw,message",
    [
        (base(users=[{"email": "t@t.in", "first_name": "A", "last_name": "B", "role": "therapist"}]), "admin is required"),
        (base(tools=["nope"]), "unknown product"),
        (base(clinic={"slug": "Bad Slug", "name": "T"}), "slug"),
        (base(clinic={"slug": "t", "name": "T", "colour": "x"}), "unknown keys"),
        (base(extra=1), "unknown top-level"),
        (
            base(users=[
                {"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"},
                {"email": "p@t.in", "first_name": "A", "last_name": "B", "role": "therapist", "tools": ["posture-tool"]},
            ]),
            "needs clinic tools",
        ),
        (
            base(users=[{"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin", "tools": ["exercise-library"]}]),
            "admin template",
        ),
        (
            base(users=[
                {"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"},
                {"email": "A@t.in", "first_name": "A", "last_name": "B", "role": "front_desk"},
            ]),
            "appears twice",
        ),
        (
            base(users=[
                {"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"},
                {"email": "f@t.in", "first_name": "A", "last_name": "B", "role": "front_desk",
                 "permissions": {"patients.create": "own"}},
            ]),
            "not allowed",
        ),
        (
            base(users=[
                {"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"},
                {"email": "f@t.in", "first_name": "A", "last_name": "B", "role": "front_desk",
                 "permissions": {"made.up": "all"}},
            ]),
            "unknown capability",
        ),
    ],
)
def test_bad_config_is_rejected(raw, message, tmp_path):
    with pytest.raises(clinic_setup.ConfigError, match=message):
        clinic_setup.parse_config(raw, tmp_path)


def test_override_to_none_removes_a_preset_capability(tmp_path):
    raw = base(users=[
        {"email": "a@t.in", "first_name": "A", "last_name": "B", "role": "admin"},
        {"email": "f@t.in", "first_name": "A", "last_name": "B", "role": "front_desk",
         "permissions": {"invoices.create": "none"}},
    ])
    cfg = clinic_setup.parse_config(raw, tmp_path)
    assert "invoices.create" not in cfg.users[1].desired_permissions()


def test_logo_rules(tmp_path):
    png = tmp_path / "logo.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)
    assert clinic_setup.logo_data_url("logo.png", tmp_path).startswith("data:image/png;base64,")
    assert clinic_setup.logo_data_url("https://x.in/l.png", tmp_path) == "https://x.in/l.png"
    (tmp_path / "logo.gif").write_bytes(b"GIF89a")
    with pytest.raises(clinic_setup.ConfigError, match="PNG, JPEG or WebP"):
        clinic_setup.logo_data_url("logo.gif", tmp_path)
    big = tmp_path / "big.png"
    big.write_bytes(b"0" * (clinic_setup.LOGO_MAX_BYTES + 1))
    with pytest.raises(clinic_setup.ConfigError, match="max"):
        clinic_setup.logo_data_url("big.png", tmp_path)
    with pytest.raises(clinic_setup.ConfigError, match="not found"):
        clinic_setup.logo_data_url("missing.png", tmp_path)


def test_credentials_file_is_private(tmp_path):
    out = tmp_path / "c" / "creds.tsv"
    clinic_setup.write_credentials(out, "s", {"a@t.in": "pw"})
    assert oct(out.stat().st_mode & 0o777) == "0o600"
    assert out.read_text() == "s\ta@t.in\tpw\n"


def test_demo_phones_are_one_fixed_series():
    from tests.seed import demo_phone

    phones = [demo_phone(i) for i in range(30)] + [demo_phone(100 + j) for j in range(15)]
    assert len(set(phones)) == 45
    assert all(p.startswith("90000") and len(p) == 10 and p.isdigit() for p in phones)
