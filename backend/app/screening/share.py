"""Provider-shared report: resources and the patient-friendly summary (S-D-039).

Founders' decision (F2 follow-up, 7 Nov 2026): after the consultation the
provider may share a report. The patient sees the provider's advice first,
then a sanitised score summary ("PHQ-9 score: 18 out of 27. Elevated
indicators of low mood or tiredness."), then the resources the provider
ticked. Internal labels (band names such as "Severe", referral and risk
flags) never reach the patient.

Pure code: no database, no I/O, so it is fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.screening.registry import RETIRED, get_instrument
from app.screening.scoring import score


@dataclass(frozen=True)
class Resource:
    key: str
    title: str
    description: str
    url: str | None = None
    phones: tuple[tuple[str, str], ...] = ()  # (label, tel number)
    source: str | None = None


# Every link was opened and checked on 9 Nov 2026. Change a link only after
# opening it again. Tele-MANAS has no verified official web page, so it
# carries the verified numbers (PIB, 11 Feb 2026) instead of a link.
RESOURCES: tuple[Resource, ...] = (
    Resource(
        key="tele_manas",
        title="Tele-MANAS mental health helpline",
        description="Free, confidential support from the Government of India, 24 hours a day, in many Indian languages.",
        phones=(("14416", "14416"), ("1-800-891-4416", "18008914416")),
    ),
    Resource(
        key="sleep_hygiene",
        title="Guide to sleep hygiene",
        description="Simple habits for falling asleep faster and sleeping better.",
        url="https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/how-to-fall-asleep-faster-and-sleep-better/",
        source="NHS",
    ),
    Resource(
        key="muscle_relaxation",
        title="Progressive muscle relaxation",
        description="Tense and release each muscle group in turn to ease physical tension.",
        url="https://uclh.nhs.uk/patients-and-visitors/patient-information-pages/relaxation-techniques",
        source="UCLH, NHS",
    ),
    Resource(
        key="pain_stress",
        title="Understanding the pain-stress connection",
        description="A short animation by pain scientist Lorimer Moseley on how persistent pain works.",
        url="https://www.tamethebeast.org/",
        source="Tame the Beast",
    ),
    Resource(
        key="breathing",
        title="Breathing exercise for stress",
        description="A calming breathing exercise you can do sitting, standing or lying down.",
        url="https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/",
        source="NHS",
    ),
)
RESOURCES_BY_KEY = {r.key: r for r in RESOURCES}

# Founders: 3 or 4 quick-fill chips under the advice box.
ADVICE_CHIPS: tuple[str, ...] = (
    "Focus on the breathing exercises we practised.",
    "Review your sleep routine using the guide below.",
    "As discussed, let's monitor this over the next 2 weeks.",
    "Keep up your exercise programme; it helps mood and pain.",
)

ADVICE_MAX = 2000
CUSTOM_LINKS_MAX = 3
CUSTOM_TITLE_MAX = 80
CUSTOM_URL_MAX = 500

# Patient-facing wording per instrument and band level. Level 0 is the
# lowest band. "Elevated" covers every band at or above the referral line,
# so the patient never reads "Severe" out of context.
_PHRASES: dict[str, tuple[str, str, str]] = {
    "phq9": (
        "Within the typical range.",
        "Mild indicators of low mood or tiredness.",
        "Elevated indicators of low mood or tiredness.",
    ),
    "gad7": (
        "Within the typical range.",
        "Mild indicators of worry or tension.",
        "Elevated indicators of worry or tension.",
    ),
}

SHAREABLE_INSTRUMENTS = frozenset(_PHRASES)


@dataclass(frozen=True)
class SummaryLine:
    instrument_id: str
    short_name: str
    score: int
    max_score: int
    phrase: str


def summary_line(instrument_id: str, instrument_version: str, responses: dict[str, int]) -> SummaryLine:
    """Patient-friendly line for one completed screener. No flags, no band names."""
    if instrument_id not in SHAREABLE_INSTRUMENTS or instrument_id in RETIRED:
        raise ValueError(f"{instrument_id} is not shareable")
    instrument = get_instrument(instrument_id, instrument_version)
    result = score(instrument, responses)
    (scale,) = result.scales  # PHQ-9 and GAD-7 have one scale each
    low, mild, elevated = _PHRASES[instrument_id]
    phrase = low if scale.band_level == 0 else mild if scale.band_level == 1 else elevated
    return SummaryLine(
        instrument_id=instrument_id,
        short_name=instrument.short_name,
        score=scale.score,
        max_score=scale.max_score,
        phrase=phrase,
    )


def clean_custom_link(title: str, url: str) -> tuple[str, str]:
    """Validate a provider's own link. Only https, no credentials, a real host."""
    title = " ".join(title.split())
    url = url.strip()
    if not title or len(title) > CUSTOM_TITLE_MAX:
        raise ValueError(f"Give each link a title of 1 to {CUSTOM_TITLE_MAX} characters.")
    if len(url) > CUSTOM_URL_MAX:
        raise ValueError("That link is too long.")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme != "https" or "." not in host or parts.username or parts.password:
        raise ValueError("Links must start with https:// and point to a website.")
    return title, url


def link_domain(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return host.removeprefix("www.")
