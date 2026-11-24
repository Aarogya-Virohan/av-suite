# Control Center e2e (L8)

Playwright against a LOCAL backend and a local Postgres. Never staging, never production:
it suspends clinics and deactivates operators.

    # once: a python 3.12 venv with backend/requirements.txt, Postgres 16 running locally,
    # and @playwright/test installed outside the app (symlink it as e2e/node_modules)
    cd frontend/control-center
    PG_RUN_AS=<pg os user> VENV=<venv> e2e/local-stack.sh up     # fresh DB, seed, 3 operators via CLI, backend :8000, console :3006
    cd e2e && npx playwright test --project=desktop-1440
    cd .. && VENV=<venv> e2e/local-stack.sh up                    # operators start un-enrolled again
    cd e2e && npx playwright test --project=mobile-390

Credentials and keys are generated into /tmp/l8-stack/stack.env (0600), never printed.
Screenshots: e2e/shots/<project>/. Mock mode smoke: `MOCK_SMOKE=1 CC_URL=http://localhost:3007 npx playwright test mock-smoke`
against `next dev -p 3007`.

Bundle gate after `next build`: `npm run check:bundle -- http` (no mock code, no secret-like text).
