"""The migration chain must have exactly one head.

Two heads make `alembic upgrade head` fail on deploy (Railway runs it as the
pre-deploy command). Every branch that brings in another branch's migrations
adds one merge revision; this test catches a missing one before a merge.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _script() -> ScriptDirectory:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config)


def test_single_alembic_head():
    heads = _script().get_heads()
    assert len(heads) == 1, f"expected one Alembic head, found {sorted(heads)}"


def test_el_nov_and_dev_heads_are_joined():
    script = _script()
    head = script.get_current_head()
    ancestors = {rev.revision for rev in script.walk_revisions("base", head)}
    assert {"a3d8f1c5e7b2", "f2b6c8d0a134"} <= ancestors
