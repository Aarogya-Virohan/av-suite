# AV Suite Screening (Tool 03)

Standalone Next.js app for psycho-social screening: staff views (worklist, patient page, results, access) and the public patient screener at `/screener/[token]`. It talks to the shared FastAPI backend.

## Run locally

1. Backend on port 8000 with this app's origin allowed: add `http://localhost:3005` to `CORS_ORIGINS` in `backend/.env`, then run the migrations (`alembic upgrade head`).
2. In this folder: `npm install`, then `npm run dev` (port 3005).
3. `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`.

## Checks

- `npm run typecheck`, `npm run lint`, `npm test` (vitest), `npm run build`
- `npm run e2e`: Playwright at phone (390 px) and desktop (1440 px) widths against a running backend and `npm start`. Test data is created through the API, no seed script. Set `CHROMIUM_PATH` if your Playwright browsers live elsewhere.

## Design system

`src/app/globals.css`, `src/components/ui/brand.tsx`, `src/components/ui/SlideOver.tsx` and `src/lib/cn.ts` are verbatim copies from `frontend/crm` at commit 619502675d60dacd0226c074cb1b506258c9f955. Do not edit them here. App-only styles go in `src/app/app.css`.
