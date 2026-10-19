# Tool 03 Psycho-Social Screening: Pending

| ID | Item | Owner | Status | Blocking |
|---|---|---|---|---|
| P-01 | Confirm a separate `frontend/psychosocial` app (new Vercel project, new CORS origin) | Onkar | Asked 20 Oct | Blocks frontend scaffold only |
| P-02 | Sparsh's chatbot branch name | Onkar | Asked 20 Oct | No (after Tool 03) |
| P-03 | Founder answers F1 to F6 (item 9 rule, post-submit message, admin visibility, real-time alert, who assigns and link expiry, consent text) | Founders | Safe defaults built; message to be drafted with the demo | No |
| P-04 | Rate limiter for public screener endpoints: add a small dependency (e.g. slowapi) or write an in-process limiter. Note Railway may run more than one replica, which makes in-process limits per replica. | Onkar | Open | Blocks the public API commit |
| P-05 | `AV_Suite_Clinical_Reference_v1.xlsx` (Severity_Logic sheet) referenced by the SRS | Onkar | Open | No, but needed before the validation report is final |
| P-06 | Re-verify Tele-MANAS (14416, Ministry of Health and Family Welfare) number and wording on the official site before it goes on a patient screen | Us | Open | No |
| P-07 | Sign-off on S-D-002, S-D-004 (DASS instruction wording), S-D-006, S-D-008 | Onkar | Open | No |
| P-08 | Add `screening.assign`, `screening.view`, `screening.refer` to the CRM permission grid (`frontend/crm/src/config/permissions.ts`) | CRM Project | Open | No, the Tool 03 app has its own access page |
