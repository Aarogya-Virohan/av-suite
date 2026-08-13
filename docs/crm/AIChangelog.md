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

*New entries go at the BOTTOM. Oldest entries at top.*
*Every AI session must add an entry before ending.*
