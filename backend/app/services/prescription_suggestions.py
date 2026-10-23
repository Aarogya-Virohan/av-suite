"""
Quick-pick suggestions for the prescription builder (founders' feedback,
23 Oct 2026: "tap to choose, multiple options, which grow over time with
what users write").

Suggestions come only from what this clinic's staff already wrote:
- exercise notes (`prescription_items.note`), split into phrases at commas,
  semicolons and line breaks;
- patient guidance (`prescriptions.physio_notes`), split into sentences.

Nothing is invented here (D-008). A phrase written more often ranks
higher; ties go to the more recent one. Phrases are grouped ignoring case
and spacing, and shown in their most recent spelling.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prescription import Prescription, PrescriptionItem

# How far back to look, and how many to return.
SCAN_LIMIT = 1000
RETURN_LIMIT = 12
MIN_LEN = 3
MAX_LEN = 140

_NOTE_SPLIT = re.compile(r"[,;\n]+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_SPACES = re.compile(r"\s+")


@dataclass
class _Tally:
    text: str
    count: int
    last: datetime


def _clean(phrase: str) -> str:
    phrase = _SPACES.sub(" ", phrase).strip().strip(".").strip()
    if phrase and phrase[0].islower():
        phrase = phrase[0].upper() + phrase[1:]
    return phrase


def rank_phrases(
    rows: Iterable[tuple[Optional[str], datetime]],
    splitter: re.Pattern[str],
    limit: int = RETURN_LIMIT,
) -> list[str]:
    """Split each text, group equal phrases, rank by count then recency."""
    tally: dict[str, _Tally] = {}
    for text, when in rows:
        if not text:
            continue
        for raw in splitter.split(text):
            phrase = _clean(raw)
            if not (MIN_LEN <= len(phrase) <= MAX_LEN):
                continue
            key = phrase.lower()
            entry = tally.get(key)
            if entry is None:
                tally[key] = _Tally(phrase, 1, when)
            else:
                entry.count += 1
                if when >= entry.last:
                    entry.last = when
                    entry.text = phrase
    ranked = sorted(tally.values(), key=lambda t: (-t.count, -t.last.timestamp()))
    return [t.text for t in ranked[:limit]]


async def get_note_suggestions(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    physio_id: Optional[uuid.UUID] = None,
) -> dict[str, list[str]]:
    """
    Suggestions for this clinic. With `physio_id` (OWN scope) only that
    physiotherapist's own prescriptions are used, matching the list rule.
    """
    scope = [Prescription.clinic_id == clinic_id]
    if physio_id is not None:
        scope.append(Prescription.physio_id == physio_id)

    note_rows = (
        await db.execute(
            select(PrescriptionItem.note, PrescriptionItem.created_at)
            .join(Prescription, Prescription.id == PrescriptionItem.prescription_id)
            .where(*scope, PrescriptionItem.note.is_not(None))
            .order_by(PrescriptionItem.created_at.desc())
            .limit(SCAN_LIMIT)
        )
    ).all()

    guidance_rows = (
        await db.execute(
            select(Prescription.physio_notes, Prescription.created_at)
            .where(*scope, Prescription.physio_notes.is_not(None))
            .order_by(Prescription.created_at.desc())
            .limit(SCAN_LIMIT)
        )
    ).all()

    return {
        "notes": rank_phrases(note_rows, _NOTE_SPLIT),
        "guidance": rank_phrases(guidance_rows, _SENTENCE_SPLIT),
    }
