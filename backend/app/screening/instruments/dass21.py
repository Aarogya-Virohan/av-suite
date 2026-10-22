"""DASS-21, Depression Anxiety Stress Scales (short form).

Source: Lovibond SH, Lovibond PF. Manual for the Depression Anxiety Stress
Scales. 2nd ed. Sydney: Psychology Foundation of Australia; 1995.

Each subscale is the sum of its 7 items multiplied by 2, so DASS-21 scores
sit on the same 0-42 scale as the full DASS-42 and use its severity cut-offs.
"""

from app.screening.types import Band, Instrument, Item, ResponseOption, Scale

_OPTIONS = (
    ResponseOption(0, "Did not apply to me at all"),
    ResponseOption(1, "Applied to me to some degree, or some of the time"),
    ResponseOption(2, "Applied to me to a considerable degree, or a good part of time"),
    ResponseOption(3, "Applied to me very much, or most of the time"),
)

_TEXTS = (
    "I found it hard to wind down",
    "I was aware of dryness of my mouth",
    "I couldn't seem to experience any positive feeling at all",
    "I experienced breathing difficulty (eg, excessively rapid breathing, "
    "breathlessness in the absence of physical exertion)",
    "I found it difficult to work up the initiative to do things",
    "I tended to over-react to situations",
    "I experienced trembling (eg, in the hands)",
    "I felt that I was using a lot of nervous energy",
    "I was worried about situations in which I might panic and make a fool "
    "of myself",
    "I felt that I had nothing to look forward to",
    "I found myself getting agitated",
    "I found it difficult to relax",
    "I felt down-hearted and blue",
    "I was intolerant of anything that kept me from getting on with what I "
    "was doing",
    "I felt I was close to panic",
    "I was unable to become enthusiastic about anything",
    "I felt I wasn't worth much as a person",
    "I felt that I was rather touchy",
    "I was aware of the action of my heart in the absence of physical "
    "exertion (eg, sense of heart rate increase, heart missing a beat)",
    "I felt scared without any good reason",
    "I felt that life was meaningless",
)

_ITEMS = tuple(Item(f"dass21_{n}", n, text) for n, text in enumerate(_TEXTS, start=1))


def _ids(*numbers: int) -> tuple[str, ...]:
    return tuple(f"dass21_{n}" for n in numbers)


# Referral at Severe or above (SRS 4.1.3), i.e. band level >= 3.
_SEVERE = 3

DASS21 = Instrument(
    id="dass21",
    version="1.0.0",
    name="Depression Anxiety Stress Scales-21",
    short_name="DASS-21",
    instructions=(
        "Please read each statement and choose the option which indicates how "
        "much the statement applied to you over the past week. There are no "
        "right or wrong answers. Do not spend too much time on any statement."
    ),
    options=_OPTIONS,
    items=_ITEMS,
    scales=(
        Scale(
            id="depression",
            label="DASS-21 Depression",
            item_ids=_ids(3, 5, 10, 13, 16, 17, 21),
            multiplier=2,
            max_score=42,
            bands=(
                Band(0, 9, "Normal", 0),
                Band(10, 13, "Mild", 1),
                Band(14, 20, "Moderate", 2),
                Band(21, 27, "Severe", 3),
                Band(28, None, "Extremely severe", 4),
            ),
            referral_min_level=_SEVERE,
        ),
        Scale(
            id="anxiety",
            label="DASS-21 Anxiety",
            item_ids=_ids(2, 4, 7, 9, 15, 19, 20),
            multiplier=2,
            max_score=42,
            bands=(
                Band(0, 7, "Normal", 0),
                Band(8, 9, "Mild", 1),
                Band(10, 14, "Moderate", 2),
                Band(15, 19, "Severe", 3),
                Band(20, None, "Extremely severe", 4),
            ),
            referral_min_level=_SEVERE,
        ),
        Scale(
            id="stress",
            label="DASS-21 Stress",
            item_ids=_ids(1, 6, 8, 11, 12, 14, 18),
            multiplier=2,
            max_score=42,
            bands=(
                Band(0, 14, "Normal", 0),
                Band(15, 18, "Mild", 1),
                Band(19, 25, "Moderate", 2),
                Band(26, 33, "Severe", 3),
                Band(34, None, "Extremely severe", 4),
            ),
            referral_min_level=_SEVERE,
        ),
    ),
    citation=(
        "Lovibond SH, Lovibond PF. Manual for the Depression Anxiety Stress "
        "Scales. 2nd ed. Sydney: Psychology Foundation of Australia; 1995."
    ),
    licence_note=(
        "The DASS is in the public domain per its authors; electronic use "
        "should reference the DASS website (www2.psy.unsw.edu.au/dass)."
    ),
)
