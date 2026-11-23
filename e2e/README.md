# AV Suite smoke suite (launch-plan EN-3)

Playwright checks for the launch flows, at 1440 px and 390 px, timezone
Asia/Kolkata. Every step saves a screenshot; `npm run pdf` turns them into one
PDF with a results table (the test pack Onkar reviews).

| # | Flow | App |
|---|---|---|
| 01 | Login (wrong password, then sign in, dashboard) | CRM |
| 02 | Add a lead | CRM |
| 03 | Add a patient, find it, open the record | CRM |
| 04 | Create an invoice, open the invoice preview | CRM |
| 05 | Build an Rx, save and download the PDF (checks `%PDF`) | Exercise Library |
| 06 | Posture from a CRM patient: locked patient, report, PDF, open it again, PDF again | CRM + Posture tool |
| 06b | Posture opened directly: pick a patient, no free text | Posture tool |
| 07 | Send a Tool 03 screener (PHQ-9 + GAD-7), link created, API confirms | Screening |

Flows 04, 05 and 07 use one shared patient that the suite creates through the
API (`Smoke Shared <run id>`), so each test also runs on its own. All rows get
a run id, so reruns never collide. Demo phones stay in the 90000 series.

Flow 06 needs real photos of a standing person: set `E2E_POSTURE_IMAGES` to a
folder with three images whose sorted names are front, side, back. Without it
the test fills the form and is reported as skipped. Real camera capture stays
a manual check.

## Run in the container (local stack)

```
cd backend && source <venv>/bin/activate       # backend requirements
AV_SEED_PASSWORD='<demo password>' ../e2e/scripts/local-stack.sh --build   # first time
AV_SEED_PASSWORD='<demo password>' ../e2e/scripts/local-stack.sh            # later runs
cd ../e2e && npm ci && E2E_PASSWORD='<demo password>' npx playwright test && npm run pdf
```

`local-stack.sh` drops and recreates the local database `av_smoke` (localhost
only), runs `alembic upgrade head` and `tests/seed.py --staging --reset`, then
starts the API on :8000 and CRM :3000, Exercise Library :3001, Posture :3002,
Screening :3005.

## Run against staging

```
cd e2e && npm ci
E2E_API_URL=https://<staging api> \
E2E_CRM_URL=https://<crm staging alias> \
E2E_EL_URL=https://<el staging alias> \
E2E_POSTURE_URL=https://<posture staging alias> \
E2E_SCREENING_URL=https://<screening staging alias> \
E2E_PASSWORD='<demo password>' npx playwright test && npm run pdf
```

The suite writes data. Remote hosts must contain "staging" (Vercel `-git-staging-` alias, staging Railway domain) or be listed in `E2E_ALLOW_HOSTS`; it always refuses the production API host
(`av-suite-production.up.railway.app`) and any host in `E2E_FORBIDDEN_HOSTS`.
Output: `out/smoke-report.pdf`, screenshots in `out/shots/`, Rx PDFs in
`out/artifacts/` (all ignored by git).
