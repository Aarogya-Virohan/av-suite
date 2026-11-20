# Hub smoke (L1: HUB-1..HUB-4, HUB-6)

One URL, one login, tools launcher. Runs against a hub stack:
CRM built with NEXT_PUBLIC_BASE_PATH=/crm and HUB_{POSTURE,EXERCISES,SCREENING}_ORIGIN,
each tool built with its own NEXT_PUBLIC_BASE_PATH (/posture, /exercises, /screening)
and NEXT_PUBLIC_HUB_ORIGIN. Demo seed (EN-1) on a local DB.

    cd e2e-hub
    ln -sf ../frontend/psychosocial/node_modules node_modules   # @playwright/test
    AV_SEED_PASSWORD=... HUB_PSQL=postgresql://postgres:postgres@localhost:5432/<db> npx playwright test

HUB_PSQL must be a local database (test 5 switches one product off and back on).
Screenshots in ./shots. HUB_URL for another host (staging only).
