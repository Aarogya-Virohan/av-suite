"""GAD-7, Generalized Anxiety Disorder scale.

Source: Spitzer RL, Kroenke K, Williams JB, Lowe B. A brief measure for
assessing generalized anxiety disorder: the GAD-7. Arch Intern Med.
2006;166(10):1092-1097. Item and option wording follows the published form.
"""

from app.screening.instruments.common import (
    DIFFICULTY_OPTIONS,
    DIFFICULTY_TEXT,
    FREQUENCY_OPTIONS,
)
from app.screening.types import Band, Instrument, Item, Scale

_ITEMS = (
    Item("gad7_1", 1, "Feeling nervous, anxious, or on edge"),
    Item("gad7_2", 2, "Not being able to stop or control worrying"),
    Item("gad7_3", 3, "Worrying too much about different things"),
    Item("gad7_4", 4, "Trouble relaxing"),
    Item("gad7_5", 5, "Being so restless that it is hard to sit still"),
    Item("gad7_6", 6, "Becoming easily annoyed or irritable"),
    Item("gad7_7", 7, "Feeling afraid, as if something awful might happen"),
    Item("gad7_difficulty", 8, DIFFICULTY_TEXT, scored=False, options=DIFFICULTY_OPTIONS),
)

GAD7 = Instrument(
    id="gad7",
    version="1.0.0",
    name="Generalized Anxiety Disorder-7",
    short_name="GAD-7",
    instructions=(
        "Over the last 2 weeks, how often have you been bothered by the "
        "following problems?"
    ),
    options=FREQUENCY_OPTIONS,
    items=_ITEMS,
    scales=(
        Scale(
            id="total",
            label="GAD-7",
            item_ids=tuple(f"gad7_{n}" for n in range(1, 8)),
            max_score=21,
            bands=(
                Band(0, 4, "None-minimal", 0),
                Band(5, 9, "Mild", 1),
                Band(10, 14, "Moderate", 2),
                Band(15, 21, "Severe", 3),
            ),
            # SRS 4.1.3: GAD-7 >= 10 (Moderate or above).
            referral_min_level=2,
        ),
    ),
    citation=(
        "Spitzer RL, Kroenke K, Williams JB, Lowe B. A brief measure for "
        "assessing generalized anxiety disorder: the GAD-7. Arch Intern Med. "
        "2006;166(10):1092-1097."
    ),
    licence_note=(
        "Developed by Drs. Spitzer, Williams, Kroenke and colleagues with an "
        "educational grant from Pfizer Inc. No permission required to "
        "reproduce, translate, display or distribute."
    ),
)
