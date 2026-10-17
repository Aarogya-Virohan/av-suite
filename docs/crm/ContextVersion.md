# ContextVersion.md — Model and Context Version Pins
> **Purpose**: Know exactly which AI model made which call, and what context
> snapshot it was working with. When a decision seems wrong in hindsight,
> you can trace it to the model and the information it had at the time.

---

## Why This Matters

Different AI models have different reasoning patterns, different knowledge cutoffs,
and different tendencies (e.g., one model might prefer verbose abstractions,
another might prefer minimal code). When you see a pattern in the code and ask
"why is it done this way?", this file tells you who made that call and with what
context — not just what was in git.

---

## Context Version Format

```markdown
### [CV-NNN] Context Snapshot — [Date]
- **Model**: [Full model name]
- **Session ID / Conversation**: [ID if available]
- **Branch at time**: [git branch]
- **Key files read this session**: [list]
- **Context gaps (files NOT read)**: [what the model didn't see]
- **Decisions made with this context**: D-NNN, D-NNN
- **Confidence level**: High / Medium / Low
  (High = read all relevant files; Low = worked from partial context)
```

---

## Context Version Log

---

### [CV-001] Context Snapshot — 2026-08-13

- **Model**: Claude Sonnet 4.6 (Thinking)
- **Session ID**: e41b6761-18c7-4a0d-80e3-f3570782df7e
- **Branch at time**: `integration/crm-merge`
- **Key files read this session**:
  - `AI_RULES.md` — full read
  - `backend/app/main.py` — full read
  - `backend/app/api/v1/router.py` — full read
  - `frontend/crm/src/app/(dashboard)/dashboard/page.tsx` — full read
  - `frontend/crm/src/store/index.ts` — full read
  - `frontend/crm/src/lib/api-client.ts` — full read
  - `frontend/crm/src/lib/auth.ts` — directory listed
  - `frontend/crm/src/features/leads/api.ts` — full read
  - `frontend/crm/src/features/analytics/api.ts` — directory listed (1 file)
  - Directory listings: all major folders in frontend/crm/src/, backend/app/
  - `docs/crm/` directory (pre-existing: CLAUDE.md, FRONTEND_ARCHITECTURE_PLAN.md, AV_Suite_CRM_Frontend_Spec_FINAL.md — listed but not read)
  - `docs/known_limitations.md` — existence noted, not read
  - Previous conversation summary: Session 5d869ef3 (CRM RBAC Schema analysis)

- **Context gaps (files NOT read)**:
  - `frontend/crm/docs/CLAUDE.md` — exists, not read this session
  - `frontend/crm/docs/FRONTEND_ARCHITECTURE_PLAN.md` — exists, not read
  - `frontend/crm/docs/AV_Suite_CRM_Frontend_Spec_FINAL.md` — exists, not read
  - `backend/app/middleware/clinic_gate.py` — existence confirmed in main.py, file not read directly
  - `backend/app/core/config.py` — existence confirmed in main.py, file not read
  - `backend/app/models/` — not read (all model files)
  - `backend/app/services/` — not read
  - `backend/app/repositories/` — not read
  - `frontend/crm/src/components/` (layout/AppShell, auth/ etc.) — not read
  - `frontend/crm/src/types/api.ts` — not read
  - `frontend/crm/src/providers/` — not read
  - `openapi.yaml` / `openapi.json` — not read (large files, 189KB / 284KB)
  - `schema.sql` — not read

- **Decisions made with this context**: D-001 through D-008 (all 8 founding decisions)

- **Confidence level**: Medium
  - High confidence on: entry points, request lifecycle, middleware order, API client pattern, auth flow
  - Medium confidence on: exact Pydantic schemas, full model relationships, feature completeness
  - Low confidence on: current state of individual feature pages (leads, patients, appointments, billing)
    — directories were listed but component files were not read individually

- **What the next session should read to complete context**:
  1. `frontend/crm/docs/CLAUDE.md` — may contain session-specific instructions
  2. `frontend/crm/docs/FRONTEND_ARCHITECTURE_PLAN.md` — earlier architecture decisions
  3. `backend/app/middleware/clinic_gate.py` — exact public path list, token extraction logic
  4. `backend/app/core/config.py` — all settings and defaults
  5. `frontend/crm/src/types/api.ts` — all TypeScript interfaces (important before touching types)
  6. Specific feature component folders before working on those features

---

## Model Capability Notes

### Claude Sonnet 4.6 (Thinking)
- Good at: reasoning through multi-file architecture, identifying security implications
- Tendency: detailed documentation, explicit reasoning chains
- Watch for: may produce verbose documentation; trim where needed
- Cannot: run code, check if API endpoints return correct data, access browser

### Model Comparison (for future reference)
*Add notes here as different models are used on this project*

| Model | Session(s) | Known strengths in this project | Known gaps |
|---|---|---|---|
| Claude Sonnet 4.6 (Thinking) | CV-001 (2026-08-13) | Architecture reasoning, docs | Didn't read all feature files |

---

*Last updated: 2026-08-13*
*Every AI session should add a CV-NNN entry before ending.*
