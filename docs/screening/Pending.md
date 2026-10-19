# Tool 03 Psycho-Social Screening: Pending

| ID | Item | Owner | Status | Blocking |
|---|---|---|---|---|
| P-01 | Separate `frontend/psychosocial` app | Onkar | Approved 20 Oct. Local build and test only. Vercel project and CORS origin are added by Onkar at deploy time. | No |
| P-02 | Sparsh's chatbot branch name | Onkar | Later, not needed for Tool 03 | No |
| P-03 | Founder answers F1 to F6 (item 9 rule, post-submit message, admin visibility, real-time alert, who assigns and link expiry, consent text) | Founders | No answers yet. Safe defaults built and marked "pending founder sign-off" in Decisions.md. Message to be drafted with the demo. | No |
| P-04 | Railway env var `SCREENER_CLIENT_IP_HEADER=X-Real-IP` (S-D-018). Optional but recommended, set before merge. | Onkar | Open | No |
| P-05 | `AV_Suite_Clinical_Reference_v1.xlsx` (Severity_Logic sheet) | Onkar | Onkar is looking for it to upload to the Project | No |
| P-06 | Tele-MANAS number | Us | Done 20 Oct: 14416 or 1-800-891-4416, 24x7, per PIB release of 11 Feb 2026 | No |
| P-07 | Sign-off on proposals S-D-002, S-D-004 (DASS instruction wording), S-D-006, S-D-008, S-D-010, S-D-012 to S-D-015, S-D-018 header choice | Onkar | Open | No |
| P-08 | Add `screening.assign`, `screening.view`, `screening.refer` to the CRM permission grid (`frontend/crm/src/config/permissions.ts`) | CRM Project | Open | No, the Tool 03 app has its own access page |
| P-09 | Pre-existing on `dev`, not Tool 03: 10 backend tests fail on a clean Postgres run (appointments, bucket, patients, permissions, treatments), and `alembic check` reports enum drift on `clinics.type` and `memberships.role` | CRM Project | Found 20 Oct, reported only | No |
| P-10 | Pre-existing on `dev`: shared `get_client_ip()` used by public booking trusts `CF-Connecting-IP` and the leftmost `X-Forwarded-For` from any caller | CRM Project | Found 20 Oct, reported only | No |
| P-11 | Local run of the new app: add `http://localhost:3005` to `CORS_ORIGINS` in backend `.env` | Onkar | Open | No |
| P-12 | v1.1 list: trend chart, PDF report, recurring schedule, admin settings, aggregates and CSV, patient own-history view, CRM patient tab, Exercise Library context, deletion-on-request | Us | Not started | No |
