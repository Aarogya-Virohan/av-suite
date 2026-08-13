# AIChangelog.md — What AI Changed, and When
> **Purpose**: Track every change made by an AI session — which model, which files,
> what the change was. Humans need to be able to audit this without reading diffs.
> This is the "AI diff log" — not a git log, not a PR description. A plain-English
> record of every AI-authored change with the model that made it.

---

## Entry Format

```markdown
### [YYYY-MM-DD] Session by [Model Name]
**Session Goal**: [1 sentence]
**Branch**: [branch name]

| File | Action | Summary |
|---|---|---|
| path/to/file | Created / Modified / Deleted | What changed and why |

**Decisions Made**: D-NNN (see Decisions.md)
**Bugs Identified**: BUG-NNN (see Bug.md)
**Features Touched**: FEAT-NNN (see Feature.md)
**Notes**: [Anything the next session needs to know]
```

---

## Changelog

---

### [2026-08-13] Session by Claude Sonnet 4.6 (Thinking)

**Session Goal**: Create 15 field-guide documentation files for the CRM tool to eliminate
cold-start overhead for future AI sessions.

**Branch**: `integration/crm-merge`

| File | Action | Summary |
|---|---|---|
| `docs/crm/Architecture.md` | Created | Full system map: repo layout, stack, request lifecycle, RBAC, env vars, module ownership |
| `docs/crm/Flow.md` | Created | Execution traces for login, authenticated requests, lead CRUD, convert lead, 401 handling, dashboard analytics |
| `docs/crm/Decisions.md` | Created | 8 founding decisions (D-001 through D-008) with full reasoning |
| `docs/crm/Constraints.md` | Created | Explicit AI no-go zones across security, data, frontend, git, PHI |
| `docs/crm/Handover.md` | Created | Session transfer protocol template + this session's first handover entry |
| `docs/crm/Bug.md` | Created | Bug trail with template + 2 pre-identified issues from code review |
| `docs/crm/Feature.md` | Created | Feature delivery trail with FEAT-001 through FEAT-006 |
| `docs/crm/EntryPoints.md` | Created | Frontend + backend entry points with execution order |
| `docs/crm/Rollback.md` | Created | 6 rollback plans for high-risk operations |
| `docs/crm/TestChecklist.md` | Created | Test checklists for 8 modules + regression suite |
| `docs/crm/FieldGuide.md` | Created | Full field guide: 15 practices with reasoning |
| `docs/crm/AIChangelog.md` | Created | This file |
| `docs/crm/ContextVersion.md` | Created | Model + context version pins |

**No source code was modified** — this session was documentation-only.

**Decisions Made**: D-007 (field guide creation), D-008 (no mock data — formalized from AI_RULES)

**Bugs Identified**:
- BUG-001: Dashboard `|| 0` fallbacks may mask loading vs. empty state distinction
- BUG-002: 401 handler clears localStorage but does not call `useAuthStore.logout()` — Zustand state remains stale until page reload

**Features Touched**: FEAT-003 (documentation field guide — marked complete)

**Notes for Next Session**:
- All 13 docs are in `docs/crm/`. The `docs/` folder at repo root already had 2 files:
  `known_limitations.md` and `schema-visualizer.html`. The crm/ subdirectory is new.
- No production code was modified. The next session can safely begin feature work.
- BUG-002 is low-hanging fruit to fix: add `useAuthStore.getState().logout()` call in
  `frontend/crm/src/lib/api-client.ts` on the 401 handler branch.

---

### [2026-08-13] Session by Gemini 3.1 Pro (High)

**Session Goal**: Address Lead Developer review comments (PR #8 & #9 replacement): fix RBAC role fallback, add route guards, unify token key, standardize env vars, remove mock data, and rebase onto integration/crm-merge.

**Branch**: `feature/frontend-redesign-impl`

| File | Action | Summary |
|---|---|---|
| `frontend/crm/src/config/permissions.ts` | Modified | Explicitly deny access on `null` role instead of fallback to 'admin' |
| `frontend/crm/src/store/index.ts` | Modified | Prevent setting 'admin' when token parse fails |
| `frontend/crm/src/components/ui/AccessRestricted.tsx` | Created | Route-level RBAC guard component |
| `frontend/crm/src/app/(dashboard)/*/page.tsx` | Modified | Added route guards to settings, billing, leads |
| `frontend/crm/src/lib/api-client.ts` | Modified | Updated env var to `NEXT_PUBLIC_API_URL` across suite |
| `frontend/crm/src/features/patients/components/*.tsx` | Modified | Replaced silent success toasts with warnings |
| `frontend/crm/src/app/(dashboard)/appointments/page.tsx` | Modified | Replaced `MOCK_REQUESTS` with live API fetch |
| `docs/crm/Constraints.md` | Modified | Added new explicit rules for AI based on this session's fixes |

**Decisions Made**: D-009 (Formalize RBAC, Toast, and Mock constraints in docs)
**Bugs Identified**: None
**Features Touched**: FEAT-004, FEAT-005
**Notes**: Branch successfully rebased onto `integration/crm-merge` (commit `b8894b9`). TypeScript build is fully clean.

---
*Every AI session must add an entry before ending.*

---

### [2026-08-13] Session by Antigravity (Current Session)

**Session Goal**: Review codebase against `AI_RULES.md` and `Constraints.md` and enforce compliance.

**Branch**: `feature/frontend-redesign-impl`

| File | Action | Summary |
|---|---|---|
| `frontend/crm/src/app/(dashboard)/settings/page.tsx` | Modified | Replaced silent success toast with warning. Removed outdated "Blocked Feature" stub for users. |
| `frontend/crm/src/features/patients/components/SoapNotesTab.tsx` | Modified | Replaced silent success toasts with warnings for local-only SOAP note changes. |
| `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx` | Modified | Replaced silent success toast with warning for unwired PDF Rx generation. |

**Decisions Made**: N/A
**Bugs Identified**: BUG-003 (Unwired endpoints needing backend logic: Settings save, SOAP finalizing, PDF generation)
**Features Touched**: N/A
**Notes**: Completed comprehensive codebase review for constraints compliance. All fake successes and lingering mock stubs are cleared out or converted to explicit warnings.
