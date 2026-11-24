#!/usr/bin/env bash
# Local stack for the Control Center Playwright run (L8). LOCAL ONLY: it makes
# its own database on a local Postgres and never reads a remote URL.
#
#   PG_BIN=/usr/lib/postgresql/16/bin PG_RUN_AS=av PG_PORT=5433 PG_SOCK=/var/tmp \
#   VENV=/path/to/venv  e2e/local-stack.sh up | down
#
# up   : fresh DB, alembic head, demo seed, two Owners + one Support made with the CLI,
#        backend on :8000, Control Center (http mode) on :3006.
# Credentials and keys are written to $STACK_DIR/stack.env (chmod 600), not printed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STACK_DIR="${STACK_DIR:-/tmp/l8-stack}"
PG_BIN="${PG_BIN:-/usr/lib/postgresql/16/bin}"
PG_PORT="${PG_PORT:-5433}"
PG_SOCK="${PG_SOCK:-/var/tmp}"
PG_RUN_AS="${PG_RUN_AS:-}"
DB_NAME="${DB_NAME:-l8_console}"
VENV="${VENV:?set VENV to a python 3.12 venv with backend requirements}"
mkdir -p "$STACK_DIR"

psql_local() { if [ -n "$PG_RUN_AS" ]; then su "$PG_RUN_AS" -c "$PG_BIN/psql -h $PG_SOCK -p $PG_PORT -d postgres -v ON_ERROR_STOP=1 -c \"$1\""; else "$PG_BIN/psql" -h "$PG_SOCK" -p "$PG_PORT" -d postgres -v ON_ERROR_STOP=1 -c "$1"; fi; }

down() {
  fuser -k 8000/tcp 3006/tcp >/dev/null 2>&1 || true
}

up() {
  down
  if [ ! -f "$STACK_DIR/stack.env" ]; then
    ( umask 077
      {
        echo "JWT_SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
        echo "PLATFORM_MFA_KEY=$(python3 -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
        echo "OWNER_A_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_urlsafe(14))')"
        echo "OWNER_B_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_urlsafe(14))')"
        echo "SUPPORT_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_urlsafe(14))')"
        echo "AV_SEED_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_urlsafe(14))')"
      } > "$STACK_DIR/stack.env" )
  fi
  set -a; . "$STACK_DIR/stack.env"; set +a

  psql_local "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE)"
  psql_local "CREATE DATABASE $DB_NAME"

  export DATABASE_URL="postgresql+asyncpg://${PG_RUN_AS:-postgres}@localhost:$PG_PORT/$DB_NAME"
  export ENVIRONMENT=development SUPABASE_URL=http://localhost SUPABASE_SECRET_KEY=local-only
  export CORS_ORIGINS=http://localhost:3006 SELF_SIGNUP_ENABLED=true

  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  alembic upgrade head >"$STACK_DIR/alembic.log" 2>&1
  python tests/seed.py --staging >"$STACK_DIR/seed.log" 2>&1 || { tail -20 "$STACK_DIR/seed.log"; exit 1; }

  printf '%s\n%s\n' "$OWNER_A_PASSWORD" "$OWNER_A_PASSWORD" | python -m app.scripts.create_platform_operator create owner.a@avlocal.in "Owner A" --role owner >/dev/null 2>&1
  printf '%s\n%s\n' "$OWNER_B_PASSWORD" "$OWNER_B_PASSWORD" | python -m app.scripts.create_platform_operator create owner.b@avlocal.in "Owner B" --role owner >/dev/null 2>&1
  printf '%s\n%s\n' "$SUPPORT_PASSWORD" "$SUPPORT_PASSWORD" | python -m app.scripts.create_platform_operator create support@avlocal.in "Support One" --role support >/dev/null 2>&1

  nohup uvicorn app.main:app --port 8000 >"$STACK_DIR/api.log" 2>&1 &
  for _ in $(seq 1 40); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done
  curl -sf http://localhost:8000/health >/dev/null

  cd "$ROOT/frontend/control-center"
  if [ ! -d .next ] || [ "${REBUILD:-0}" = 1 ]; then
    NEXT_PUBLIC_PLATFORM_API_MODE=http NEXT_PUBLIC_API_URL=http://localhost:8000 npx next build >"$STACK_DIR/web-build.log" 2>&1
  fi
  NEXT_PUBLIC_PLATFORM_API_MODE=http NEXT_PUBLIC_API_URL=http://localhost:8000 nohup npx next start -p 3006 >"$STACK_DIR/web.log" 2>&1 &
  for _ in $(seq 1 40); do curl -sf http://localhost:3006/login >/dev/null 2>&1 && break; sleep 1; done
  curl -sf http://localhost:3006/login >/dev/null
  echo "stack up: api :8000, control-center :3006, db $DB_NAME"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "usage: local-stack.sh up|down" >&2; exit 2 ;;
esac
