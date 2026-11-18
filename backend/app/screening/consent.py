"""Patient consent text for Tool 03 (SRS 4.2.1).

The backend owns the text so every consent record points to the exact
wording the patient saw. Change the wording -> bump CONSENT_TEXT_VERSION,
and patients are asked again on their next link.

Status: approved by the founders for pilot clinics (F6 = 6B, S-D-016). A
legal check under the DPDP Act is required before a wider launch (P-15).
The wording below is theirs, word for word.
"""

CONSENT_TEXT_VERSION = "2026-11-07.pilot1"

CONSENT_TITLE = "Before you start"

CONSENT_PARAGRAPHS: tuple[str, ...] = (
    "Your healthcare provider has asked you to answer a few short questions "
    "about how you have been feeling lately. Stress, worry, and low mood can "
    "affect your physical health and recovery, so this helps them better plan "
    "your care.",
    "What we collect: Your answers to these questions and the date you "
    "answered them.",
    "How it is used: Your answers are scored automatically and securely shown "
    "to your healthcare provider as part of your treatment record. This is a "
    "screening check to help guide your care, not a medical diagnosis.",
    "Who can see it: Only your treating healthcare provider and you. "
    "Administrative staff cannot see your answers or scores. Your information "
    "is never shared with anyone outside your provider's practice without "
    "your explicit permission.",
    "Your choice: Your participation is completely voluntary. You can stop at "
    "any time, and you can easily withdraw your consent directly from this "
    "page. If you withdraw, no new questionnaires will be sent to you. You can "
    "also ask your healthcare provider to delete your past answers from their "
    "system at any time.",
)
