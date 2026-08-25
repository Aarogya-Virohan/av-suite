# CRM Documentation Index

> **Branch**: `integration/crm-merge`
> **Last updated**: 2026-08-13
> **Before touching any file in this project, read this index and load the relevant docs.**

---

## Cold Start Protocol (New Session Checklist)

```
1. Read this file (30 sec)
2. Read Architecture.md (5 min) — know the system
3. Read Constraints.md (3 min) — know the rules
4. Read Handover.md → latest session entry (2 min) — know the current state
5. Read the relevant feature section in Flow.md for the task at hand
```

---

## The 13 Field Guide Files

| File | Purpose | Read When |
|---|---|---|
| [Architecture.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Architecture.md) | System map — repo layout, stack, request lifecycle, auth, RBAC, module ownership | Every session start. Before touching ANY file. |
| [Flow.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Flow.md) | Execution traces — what calls what for every major user action | Before debugging or building any feature flow |
| [EntryPoints.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/EntryPoints.md) | Every frontend + backend entry point with execution order | Before modifying boot sequence, auth, or middleware |
| [Constraints.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Constraints.md) | What AI must never touch — security, data, frontend, git, PHI | Every session start. Non-negotiable. |
| [Decisions.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Decisions.md) | Why behind every architectural choice | Before questioning or changing an established pattern |
| [Handover.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Handover.md) | Session transfer protocol — current state, what's next | Start and end of every session |
| [Feature.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Feature.md) | Feature delivery trail — requirements, contracts, status | Before starting or continuing any feature |
| [Bug.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Bug.md) | Bug trail — symptom, root cause, fix, verification | When investigating or fixing bugs |
| [TestChecklist.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/TestChecklist.md) | Per-module test checklists with curl commands | Before marking anything complete |
| [Rollback.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Rollback.md) | Rollback plans for high-risk operations | Before DB migrations, deployments, middleware changes |
| [AIChangelog.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/AIChangelog.md) | What AI changed, when, and which model | When auditing or tracing AI-introduced issues |
| [ContextVersion.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/ContextVersion.md) | What each AI session read (and what it missed) | When trusting or questioning AI-authored reasoning |
| [FieldGuide.md](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/FieldGuide.md) | Full reasoning behind all 15 practices | Onboarding. Understanding why this system exists. |

---

## End-of-Session Protocol (5 min investment)

Before ending any AI session, update these files:

| File | What to add |
|---|---|
| `AIChangelog.md` | Files changed, model name, decisions made |
| `Handover.md` | Current state, what's next, blockers |
| `Decisions.md` | Any new non-obvious architectural choice |
| `ContextVersion.md` | What you read vs. what you skipped |
| `Bug.md` | Any bugs found or fixed |
| `Feature.md` | Status update for features touched |

---

## Related Files Outside This Directory

| File | Location | Purpose |
|---|---|---|
| AI Rules | [`AI_RULES.md`](file:///home/Dont_Fucking_Quit/av-suite/AI_RULES.md) | Global AI behavior rules for the entire repo |
| CRM Frontend Spec | [`frontend/crm/docs/AV_Suite_CRM_Frontend_Spec_FINAL.md`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/docs/AV_Suite_CRM_Frontend_Spec_FINAL.md) | Original requirements |
| Frontend Architecture Plan | [`frontend/crm/docs/FRONTEND_ARCHITECTURE_PLAN.md`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/docs/FRONTEND_ARCHITECTURE_PLAN.md) | Earlier architecture decisions |
| CLAUDE Instructions | [`frontend/crm/docs/CLAUDE.md`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/docs/CLAUDE.md) | Claude-specific instructions |
| Schema Visualizer | [`docs/schema-visualizer.html`](file:///home/Dont_Fucking_Quit/av-suite/docs/schema-visualizer.html) | Interactive DB schema explorer |
| Known Limitations | [`docs/known_limitations.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/known_limitations.md) | Repo-level known issues |
| OpenAPI Spec | [`openapi.yaml`](file:///home/Dont_Fucking_Quit/av-suite/openapi.yaml) | Full API contract |
