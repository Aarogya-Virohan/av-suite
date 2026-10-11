import pytest


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://user:pass@localhost:5432/test_db",
        "postgresql+asyncpg://user:pass@127.0.0.1:5432/test_db",
        "sqlite+aiosqlite:///./test.db",
        "sqlite+aiosqlite:///:memory:",
    ],
)
def test_local_test_database_urls_are_allowed(
    database_url: str, test_database_url_safety_check
):
    test_database_url_safety_check(database_url)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://user:pass@project.supabase.co:5432/postgres",
        "postgresql+asyncpg://user:pass@db.example.com:5432/app",
        "sqlite+aiosqlite://remote-host/test.db",
    ],
)
def test_remote_test_database_urls_are_refused(
    database_url: str, test_database_url_safety_check
):
    with pytest.raises(ValueError, match="Unsafe test database URL"):
        test_database_url_safety_check(database_url)
