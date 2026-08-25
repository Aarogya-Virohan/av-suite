# FieldGuide.md — The 15 Practices: Full Reasoning
> **Purpose**: The complete field guide. Each practice explained with the "why"
> that most documentation skips. This is not a rule list. It's a reasoning map.

---

## Preamble

These 15 practices exist because AI-assisted development has a failure mode that
human-only development doesn't: **context amnesia**. Every new session starts cold.
Without deliberate documentation, each session reinvents, guesses, or subtly
diverges from the established architecture.

The practices below are the immune system against that failure mode.

---

## 1. Entry Point Documentation

**The Practice**: Document exactly where code starts and what it calls next.

**Why it matters**: In a Next.js 14 App Router codebase with FastAPI backend, there are
multiple "starts" — the root layout, the provider tree, the middleware stack,
the route handler. An AI that doesn't know the execution order will add code in the
wrong place: business logic in the layout, auth in a component, fetch in a utility.

**How we do it**: [`EntryPoints.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/EntryPoints.md)
maps every entry point for both frontend and backend with explicit call chains.

**The test**: Can someone unfamiliar with the codebase answer "where does a request start
and what runs before my endpoint handler?" without opening any source file?

---

## 2. Execution Order

**The Practice**: What function calls what other function — written out, not implied.

**Why it matters**: The call chain from "user clicks Login" to "JWT stored in localStorage"
spans 6 files. An AI that doesn't know this chain will skip steps (e.g., forget to call
`initializeFromStorage()` on mount, breaking refresh persistence).

**How we do it**: [`Flow.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Flow.md)
traces every major user action with file-level granularity.

**The test**: Can you trace a bug to the exact file and function by reading Flow.md alone?

---

## 3. What Part of Code AI Changed

**The Practice**: Track which files were modified by AI, not just by humans.

**Why it matters**: AI-authored code can be subtly wrong in ways that accumulate.
If the next session doesn't know "this auth interceptor was rewritten by AI last session",
it might not question a pattern that was actually wrong.

**How we do it**: [`AIChangelog.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/AIChangelog.md)
lists every file touched by every AI session. Not a git diff — a plain English summary.

**The test**: Can a human audit every AI-made change without reading git history?

---

## 4. Handover Files

**The Practice**: Write context incrementally so the next session isn't starting from zero.

**Why it matters**: Session context is the most perishable asset in AI-assisted development.
An AI that spent 20 minutes understanding the codebase loses all of that when the session ends.
The next session pays that 20 minutes again — and again — and again. Handover files amortize
that cost across every future session.

**How we do it**: [`Handover.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Handover.md)
has a standard template. Fill it before ending any session.

**The test**: Can the next AI session know exactly what state the work is in and what to do
first — without asking the user to re-explain?

---

## 5. Decisions.md

**The Practice**: Log the "why" behind every AI decision, not just the "what".

**Why it matters**: Code shows what was done. Code comments show what code does.
Only `Decisions.md` shows why *this approach* over *that alternative*. Without it,
a future session might "improve" a design that was deliberately chosen, breaking a
constraint it didn't know existed.

**How we do it**: [`Decisions.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Decisions.md)
has numbered entries with options considered, the choice made, and the reasoning.

**The test**: When a future AI questions a pattern, can it find the reasoning in Decisions.md
before changing it?

---

## 6. Explicit Comments in Code

**The Practice**: Make the flow legible, not just functional.

**Why it matters**: The backend `main.py` has bilingual comments explaining middleware order.
Those comments aren't for the machine — they're for the next human or AI that asks
"why is CORS added after ClinicGate?" The code works either way. The comments explain
that the *order* is deliberate.

**How we do it**: Every non-obvious decision in code gets a comment that explains the *why*,
not the *what*. The *what* is readable. The *why* is invisible without comments.

**The standard**: Read a file's comments alone. Can you understand the design intent?

---

## 7. Flow.md

**The Practice**: Trace exactly how execution moves between files and functions.

**Why it matters**: In a multi-layer architecture (component → hook → apiClient → middleware
→ endpoint → service → repository → DB), bugs hide in the transitions between layers.
Flow.md names every transition so an AI can pinpoint where in the chain a bug lives.

**How we do it**: [`Flow.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Flow.md)
covers: bootstrap, login, authenticated request, create lead, convert lead, 401 handling, dashboard.

**The test**: Can you draw a sequence diagram from memory after reading Flow.md?

---

## 8. Bug.md and Feature.md

**The Practice**: A start-to-finish trail anyone can pick up cold.

**Why it matters**: Bugs and features that are "in progress" are the most dangerous context
to lose. A half-fixed bug looks like working code. A half-built feature looks like a stub.
Without a trail, the next session may mark something complete that isn't, or worse,
build over a broken foundation.

**How we do it**:
- [`Bug.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Bug.md): symptom, steps to reproduce, root cause, fix, verification
- [`Feature.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Feature.md): requirements, backend contract, implementation steps, verification

**The test**: Can an engineer who was not involved pick up an in-progress bug or feature
and continue it without talking to anyone?

---

## 9. Architecture.md

**The Practice**: The system map so nothing gets touched blind.

**Why it matters**: An AI that doesn't know the backend is shared across tools might
"optimize" the backend for CRM and break the Posture tool. An AI that doesn't know
middleware runs in reverse-add order might swap CORS and auth middleware, breaking
preflight requests.

**How we do it**: [`Architecture.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Architecture.md)
maps: repository layout, stack, request lifecycle, auth model, RBAC, state management rules,
environment variables, what shares the backend.

**The test**: Before touching any file, can an AI answer "who else uses this code?"

---

## 10. Constraints.md

**The Practice**: The things AI should never touch, spelled out.

**Why it matters**: Rules that live only in a human's head are invisible to AI.
An AI presented with "this would be cleaner with a client-side auth check" has no
reason not to add one — unless it's been told explicitly that client-side auth checks
are theater. `Constraints.md` makes implicit rules explicit.

**How we do it**: [`Constraints.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Constraints.md)
covers: auth, data, frontend architecture, git, AI behavior, PHI handling.

**The test**: Can any constraint be violated by an AI acting in good faith? If yes, add it.

---

## 11. Test Checklists

**The Practice**: Proof it works, not just a claim that it does.

**Why it matters**: "I've tested it" is not a verification. A checklist that was run
and marked is. AI sessions can't run a browser — but they can write the checklist that
a human runs. A written checklist also reveals what has never been tested.

**How we do it**: [`TestChecklist.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/TestChecklist.md)
has per-module checklists with actual `curl` commands and frontend manual steps.

**The test**: After running the checklist, is there any ambiguity about whether a feature works?

---

## 12. Rollback Plans

**The Practice**: Know your way out before you need it.

**Why it matters**: The worst time to figure out how to rollback a database migration is
after it has deleted a column in production. Rollback plans written in advance are
clear-headed. Rollback plans written during an incident are panicked.

**How we do it**: [`Rollback.md`](file:///home/Dont_Fucking_Quit/av-suite/docs/crm/Rollback.md)
has plans for: DB migrations, DB restore, frontend deployment, middleware changes,
API client changes, env var changes.

**The test**: For any high-risk operation, can a junior developer execute the rollback
alone from this document, under pressure, without calling anyone?

---

## 13. Read Every Diff

**The Practice**: Before and after — never trust generated code without reviewing it.

**Why it matters**: AI generates plausible code. Plausible and correct are not the same thing.
A diff review catches: subtle logic errors, missing edge cases, wrong variable names,
incorrect API contracts, security issues that look fine at first glance.

**How we apply it**: Every AI-generated change is reviewed before it enters the codebase.
The `AIChangelog.md` creates accountability — if a bug was introduced by AI, the entry
will name the session and the file.

**The test**: Is there any AI-authored code in the repo that was not reviewed by a human?

---

## 14. Ask "Why" Before "What"

**The Practice**: Catch bad reasoning before it becomes 200 lines of code.

**Why it matters**: An AI asked "add user search to the patients page" might add a
new Zustand store for search state, a new API endpoint, and a new component —
when the existing TanStack Query filter and existing `usePatients()` hook already
support all of it. The question "why a new store?" saves hours of cleanup.

**How we apply it**: Before writing code, reason about the approach. Document it in
Decisions.md if it's non-obvious. The user should be able to say "stop, here's why
that's wrong" before 200 lines are written.

**The test**: Is every new abstraction justified? Can you find the justification in Decisions.md?

---

## 15. One Change Per Request

**The Practice**: Small, traceable, reviewable.

**Why it matters**: Large PRs are unreviewed PRs. A change that touches 15 files
for "one feature" is actually 5 independent changes bundled together, each hiding
the others from review. Small changes are reversible. Large changes are not.

**How we apply it**:
- Each AI session has one clear goal
- Each git commit addresses one concern
- Each PR covers one feature area
- `AIChangelog.md` entries are scoped to one session's work

**The test**: Can the change be reverted without affecting unrelated functionality?

---

## End-of-Session Protocol (Summary)

Before ending any AI session:

1. Add an entry to `AIChangelog.md` — files changed, model used, decisions made
2. Add an entry to `Handover.md` — what's done, what's in progress, what's next
3. Update `Decisions.md` for any significant reasoning this session
4. Add `ContextVersion.md` entry with what was and wasn't read
5. Update `Bug.md` if any bugs were identified or fixed
6. Update `Feature.md` status for any features touched

**Time investment**: 5–10 minutes per session.
**Return**: Every future session saves 20–30 minutes of cold-start re-discovery.

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
