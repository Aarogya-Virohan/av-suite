# Tool 03 Psycho-Social Screening: Decisions

Format: context, choice, reason, decided by. Status "pending sign-off" means it is built as the safe default and can still change.

## S-D-001 Branch base
- Context: Tool 03 work starts on its own branch.
- Choice: `feat/tool03-psychosocial` from `origin/dev` at `770bc87507a541ae93700751c517de21c7dca708` (20 Oct 2026). Alembic head at that commit: `a8c4e2f1d903` (single head).
- Decided by: Onkar (handoff).

## S-D-002 Reuse the existing product key `psycho-social-screening`
- Context: the handoff proposed a new key `psychosocial-screening`. The repo already registers `psycho-social-screening` in `backend/app/core/products.py`, in migration `6b0f1d2c3a4e`, in `d0c1b2a3f4e5` (allowed clinic types) and in `frontend/av-marketplace/data/products.ts`.
- Choice: use `psycho-social-screening`. No new product row. Capability prefix mapping for it gets added in `PRODUCT_CAPABILITY_PREFIXES` when the capabilities land.
- Reason: a second key would split entitlements and break the marketplace card.
- Decided by: proposal, pending Onkar sign-off.

## S-D-003 Engine location and shape
- Choice: generic engine in `backend/app/screening/`. Instrument definitions are frozen Python dataclasses with an `id` and `version`, registered in `registry.py`. Scoring (`scoring.py`) is pure: no DB, no IO.
- Reason: definitions are reviewed in code and covered by tests. Sessions will store `instrument_id`, `instrument_version`, raw responses and computed results, so old results stay explainable. Tool 04 instruments plug in the same way.
- Decided by: Onkar (handoff section 8).

## S-D-004 Instrument wording is verbatim from the published forms
- PHQ-9 and GAD-7: item text, stems and the four options follow the published Pfizer forms, including the em-dashes inside PHQ-9 items 6 and 8 (fidelity to the instrument wins over our no-em-dash writing rule). Both are free to reproduce, no permission needed.
- DASS-21: item text and options from the Lovibond 1995 short form. One adaptation: the instruction says "choose the option" instead of "circle a number 0, 1, 2 or 3", because there is nothing to circle on screen. The DASS is public domain per its authors; we must reference the DASS website (done in `licence_note`, to be shown in the UI footer).
- Decided by: proposal, pending Onkar sign-off on the DASS instruction adaptation.

## S-D-005 PHQ-9 item 9 risk rule (founder question F1)
- Context: the SRS has no rule for item 9 (thoughts of self-harm).
- Choice: any answer above 0 on item 9 sets `risk_item_flag = true` and forces `referral_flag = true`, whatever the total.
- Decided by: safe default from handoff, pending founder sign-off.

## S-D-006 Functional difficulty question kept, not scored
- Context: both published PHQ-9 and GAD-7 forms end with "how difficult have these problems made it...". It is not part of the score.
- Choice: included as an optional, unscored item (`phq9_difficulty`, `gad7_difficulty`) so the physio sees it. It never changes the total or the band.
- Decided by: proposal, pending Onkar sign-off.

## S-D-007 DASS-21 fully scored and validated
- Context: SRS section 6 lists DASS-21 scoring validation as a stretch goal for v1.0.
- Choice: scored and tested to the same bar as PHQ-9 and GAD-7. Subscale = sum of 7 items x 2, Lovibond 1995 cut-offs. Referral at Severe or above on any subscale (SRS 4.1.3).
- Decided by: Onkar (handoff plan step 2).

## S-D-008 Band labels
- PHQ-9 and GAD-7 lowest band is labelled "None-minimal" (Kroenke 2001 / Spitzer 2006 wording) where the SRS table says "None". Score ranges are identical.
- Decided by: proposal, pending Onkar sign-off.

## S-D-009 Patients are not product-gated
- Context: a clinic may buy Tool 03 without CRM.
- Finding (verified in `core/products.py`): `patients.*` capabilities are platform-core and are not in `CAPABILITY_PRODUCT_MAP`, so a screening-only clinic can still list and pick patients. No change needed for the patient picker.
- Decided by: verified fact, recorded for the build.
