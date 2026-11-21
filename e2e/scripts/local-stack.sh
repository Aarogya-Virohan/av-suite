#!/usr/bin/env bash
# Local / container stack for the smoke suite (launch-plan EN-3).
# Fresh Postgres DB -> alembic upgrade head -> demo seed -> API + 4 frontends.
#
#   AV_SEED_PASSWORD='...' e2e/scripts/local-stack.sh [--build]
#
# Needs: a Postgres you can reach as DATABASE_URL's server (default
# postgres@localhost:5433), the backend venv active (python with
# requirements.txt), Node 22. --build runs npm ci + next build per app first.
# Never point DATABASE_URL at staging or prod here: the script DROPs the
# database named in E2E_DB (default av_smoke) before every run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PGHOST_PORT="${E2E_PG:-postgres@localhost:5433}"
DB="${E2E_DB:-av_smoke}"
: "${AV_SEED_PASSWORD:?set AV_SEED_PASSWORD (demo clinic password)}"

case "$PGHOST_PORT" in
  *localhost*|*127.0.0.1*) ;;
  *) echo "REFUSED: local-stack only drops databases on localhost" >&2; exit 2 ;;
esac

export JWT_SECRET_KEY="${JWT_SECRET_KEY:-ci-only-not-a-secret}"
export SUPABASE_URL="${SUPABASE_URL:-http://localhost}"
export SUPABASE_SECRET_KEY="${SUPABASE_SECRET_KEY:-ci-only-not-a-secret}"
export DEBUG=false ENVIRONMENT=development
export DATABASE_URL="postgresql+asyncpg://${PGHOST_PORT}/${DB}"
PSQL_URL="postgresql://${PGHOST_PORT}/postgres"

declare -A PORT=([crm]=3000 [exercise-library]=3001 [posture-tool]=3002 [psychosocial]=3005)

echo "== stopping old servers"
fuser -k 8000/tcp "${PORT[@]/%//tcp}" >/dev/null 2>&1 || true
sleep 1

echo "== fresh database $DB"
psql "$PSQL_URL" -qc "DROP DATABASE IF EXISTS $DB" -c "CREATE DATABASE $DB"
(cd "$ROOT/backend" && alembic upgrade head >/tmp/av-alembic.log 2>&1) || { tail -20 /tmp/av-alembic.log; exit 1; }
(cd "$ROOT/backend" && python tests/seed.py --staging --reset | grep -E "seeded|target")

if [[ "${1:-}" == "--build" ]]; then
  for app in "${!PORT[@]}"; do
    echo "== build $app"
    (cd "$ROOT/frontend/$app" && npx -y npm@11 ci >/dev/null \
      && echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local \
      && npx next build >/tmp/av-build-$app.log 2>&1) || { tail -30 /tmp/av-build-$app.log; exit 1; }
  done
fi

ORIGINS=""
for app in "${!PORT[@]}"; do ORIGINS+="http://localhost:${PORT[$app]},"; done
echo "== API :8000"
(cd "$ROOT/backend" && CORS_ORIGINS="${ORIGINS%,}" setsid nohup uvicorn app.main:app --port 8000 </dev/null >/tmp/av-api.log 2>&1 &)
for app in "${!PORT[@]}"; do
  echo "== $app :${PORT[$app]}"
  (cd "$ROOT/frontend/$app" && setsid nohup npx next start -p "${PORT[$app]}" </dev/null >"/tmp/av-web-$app.log" 2>&1 &)
done

for _ in $(seq 1 60); do
  ok=1
  curl -sf localhost:8000/health >/dev/null || ok=0
  for app in "${!PORT[@]}"; do curl -sf -o /dev/null "localhost:${PORT[$app]}/login" || ok=0; done
  [[ $ok == 1 ]] && { echo "== stack up"; exit 0; }
  sleep 2
done
echo "stack did not come up; see /tmp/av-*.log" >&2
exit 1
