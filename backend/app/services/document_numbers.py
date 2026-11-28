"""Server-side document numbers (D-043, decided 26 Nov 2026).

Clinical documents: <clinic code>-<TYPE>-<6 digits>, TYPE = RX, POS or PSY,
counted per clinic per type and never reset, e.g. ASC2-RX-000014.

Invoice INV-<FY>-<6 digits> and receipt RCP-<FY>-<6 digits>, counted per
clinic per Indian financial year (April to March), e.g. INV-2627-000003. No
clinic code, so the number stays within the 16 characters GST allows.

Numbers are only ever made here, inside the caller's transaction, with one
INSERT ... ON CONFLICT DO UPDATE on document_counters (the same pattern as
the old invoice_counters). Two requests at the same moment queue on the
counter row, so each gets its own number. The counter is also never allowed
to fall behind the numbers already stored on the document table, so a row
written by hand or by an older build cannot cause a duplicate. The unique
(clinic_id, number) constraint on every table is the last guard.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_numbering import DocumentCounter

IST = ZoneInfo("Asia/Kolkata")

RX = "RX"
POS = "POS"
PSY = "PSY"
INV = "INV"
RCP = "RCP"
CLINICAL_TYPES = (RX, POS, PSY)
FINANCIAL_TYPES = (INV, RCP)

# Where each type's numbers are stored (fixed names, never user input).
_STORE = {
    RX: ("prescriptions", "number"),
    POS: ("posture_sessions", "number"),
    PSY: ("psychosocial_reports", "number"),
    INV: ("invoices", "invoice_number"),
    RCP: ("payments", "receipt_number"),
}

DIGITS = 6
GST_MAX_CHARS = 16


class DocumentNumberError(RuntimeError):
    """A number cannot be given out (financial number over 16 characters)."""


def financial_year(value: datetime | date | None = None) -> str:
    """Indian financial year of a moment, as "2627" for 1 Apr 2026 - 31 Mar 2027.

    Datetimes are read in IST (a payment at 23:30 IST on 31 March belongs to
    the old year); a naive datetime is taken as UTC, as the database stores it.
    """
    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(IST).date()
    start = value.year if value.month >= 4 else value.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def format_clinical(code: str, doc_type: str, n: int) -> str:
    return f"{(code or '').strip().upper()}-{doc_type}-{n:0{DIGITS}d}"


def format_financial(doc_type: str, fy: str, n: int) -> str:
    number = f"{doc_type}-{fy}-{n:0{DIGITS}d}"
    if len(number) > GST_MAX_CHARS:
        raise DocumentNumberError(
            f"{doc_type} number {n} for FY {fy} would be longer than {GST_MAX_CHARS} characters"
        )
    return number


def _pattern(doc_type: str, period: str) -> str:
    """Regex with one group = the counter part, for the numbers of this type."""
    if doc_type in CLINICAL_TYPES:
        # The clinic code can be changed in Settings, so match any code.
        return f"^[A-Z0-9]+-{doc_type}-([0-9]+)$"
    return f"^{doc_type}-{period}-([0-9]+)$"


async def next_number(
    session: AsyncSession, clinic_id: uuid.UUID, doc_type: str, period: str = ""
) -> int:
    """Take the next counter value for (clinic, type, period). Runs in the
    caller's transaction: if that rolls back, the number is not used up."""
    if doc_type not in _STORE:
        raise ValueError(f"unknown document type {doc_type!r}")
    if doc_type in CLINICAL_TYPES:
        period = ""
    table, column = _STORE[doc_type]
    pattern = _pattern(doc_type, period)
    # The next number after the highest one already stored on the table.
    after_stored = text(
        f"""(SELECT COALESCE(MAX(substring({column} from :pat)::bigint), 0) + 1
             FROM {table} WHERE clinic_id = :seed_clinic AND {column} ~ :pat)"""
    ).bindparams(pat=pattern, seed_clinic=clinic_id)
    stmt = pg_insert(DocumentCounter).values(
        clinic_id=clinic_id,
        doc_type=doc_type,
        period=period,
        last_number=after_stored,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[DocumentCounter.clinic_id, DocumentCounter.doc_type, DocumentCounter.period],
        set_={"last_number": func.greatest(DocumentCounter.last_number + 1, after_stored)},
    ).returning(DocumentCounter.last_number)
    return int((await session.execute(stmt)).scalar_one())


async def next_clinical_number(
    session: AsyncSession, clinic_id: uuid.UUID, clinic_code: str, doc_type: str
) -> str:
    """ASC2-RX-000014 style number for a new Rx, posture report or psychosocial export."""
    if doc_type not in CLINICAL_TYPES:
        raise ValueError(f"{doc_type!r} is not a clinical document type")
    if not (clinic_code or "").strip():
        raise ValueError("a clinical number needs the clinic code")
    n = await next_number(session, clinic_id, doc_type)
    return format_clinical(clinic_code, doc_type, n)


async def next_financial_number(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    doc_type: str,
    on: datetime | date | None = None,
) -> str:
    """INV-2627-000003 / RCP-2627-000003 for a document dated `on` (IST)."""
    if doc_type not in FINANCIAL_TYPES:
        raise ValueError(f"{doc_type!r} is not a financial document type")
    fy = financial_year(on)
    n = await next_number(session, clinic_id, doc_type, fy)
    return format_financial(doc_type, fy, n)
