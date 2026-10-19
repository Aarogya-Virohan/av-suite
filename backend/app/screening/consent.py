"""Patient consent text for Tool 03 (SRS 4.2.1).

The backend owns the text so every consent record points to the exact
wording the patient saw. Change the wording -> bump CONSENT_TEXT_VERSION,
and patients are asked again on their next link.

Status: draft, pending founder approval (F6, S-D-016).
"""

CONSENT_TEXT_VERSION = "2026-10-20.draft1"

CONSENT_TITLE = "Before you start"

CONSENT_PARAGRAPHS: tuple[str, ...] = (
    "Your physiotherapist has asked you to answer a few short questions about "
    "how you have been feeling lately. Stress, worry and low mood can affect "
    "pain and recovery, so this helps them plan your care.",
    "What we collect: your answers to these questions and the date you "
    "answered them.",
    "How it is used: your answers are scored automatically and shown to your "
    "physiotherapist as part of your treatment record. This is a screening "
    "check, not a diagnosis.",
    "Who can see it: only your treating physiotherapist and you. Clinic "
    "administrators see anonymous totals only. Your answers are never shared "
    "with anyone outside the clinic.",
    "Your choice: you can stop at any time, and you can withdraw your consent "
    "from this page. If you withdraw, no new questionnaires will be sent to "
    "you. You can also ask your clinic to delete your answers.",
)
