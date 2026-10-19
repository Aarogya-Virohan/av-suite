# Tool 03 Psycho-Social Screening: Known Limitations

| ID | Limitation | Impact | Planned fix |
|---|---|---|---|
| S-L-001 | The repo has no rate limiter (checked: no slowapi or custom limiter in `backend/app` or `requirements.txt`). The public booking page relies on Turnstile only. | Public screener endpoints need one before they ship. | Decision needed before the API commit (see Pending P-04). v1.0. |
| S-L-002 | No column-level encryption. At rest we rely on Supabase disk encryption, in transit on HTTPS. | Meets the SRS wording at infrastructure level only. Column encryption needs a key-management decision. | v1.1 or later, after a founder decision. |
| S-L-003 | The SRS refers to `AV_Suite_Clinical_Reference_v1.xlsx` (Severity_Logic sheet) for referral thresholds. We do not have that file. Thresholds are built from SRS 4.1.3 and the published papers. | If that sheet differs from SRS 4.1.3, we would not know. | Get the file from Onkar (Pending P-05). |
