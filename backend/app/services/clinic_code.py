"""Clinic code: the short prefix of the Patient ID ("ADP" in ADP-000003).

Until 24 Nov 2026 the CRM worked the prefix out of the clinic name on every
screen (frontend/crm/src/lib/patientNumber.ts). It is now stored in
clinics.code so it can be printed on PDFs and WhatsApp texts and edited in
Settings. New clinics get the same value the old rule gave; if another clinic
already has it, a number is added (ADP, ADP2, ADP3).

The migration 20261124_clinics_code.py carries its own copy of derive_clinic_code
so it never depends on app code; tests/test_clinic_code.py keeps the two equal.
"""

from __future__ import annotations

import re

CODE_PATTERN = re.compile(r"^[A-Z0-9]{1,6}$")
CODE_MAX_LENGTH = 6
DEFAULT_CODE = "PT"
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def derive_clinic_code(clinic_name: str | None) -> str:
    """First letter of up to 3 words, or the first 3 letters of a one-word name."""
    words = _WORD.findall(clinic_name or "")
    if not words:
        return DEFAULT_CODE
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def normalize_clinic_code(value: str) -> str:
    """Trim and upper-case what a person typed. Raises ValueError if it is not
    1 to 6 letters or digits."""
    code = (value or "").strip().upper()
    if not CODE_PATTERN.fullmatch(code):
        raise ValueError("Clinic code must be 1 to 6 letters or digits (A-Z, 0-9).")
    return code


def next_free_code(base: str, taken: set[str]) -> str:
    """base, else base2, base3, ... that is not in taken (kept within 6 characters)."""
    if base not in taken:
        return base
    n = 2
    while True:
        suffix = str(n)
        candidate = base[: CODE_MAX_LENGTH - len(suffix)] + suffix
        if candidate not in taken:
            return candidate
        n += 1
