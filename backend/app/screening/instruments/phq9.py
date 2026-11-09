"""PHQ-9, Patient Health Questionnaire (depression).

Source: Kroenke K, Spitzer RL, Williams JB. The PHQ-9: validity of a brief
depression severity measure. J Gen Intern Med. 2001;16(9):606-613.
Item and option wording follows the published PHQ-9 form verbatim.
"""

from app.screening.instruments.common import (
    DIFFICULTY_OPTIONS,
    DIFFICULTY_TEXT,
    FREQUENCY_OPTIONS,
)
from app.screening.types import Band, Instrument, Item, RiskItemRule, Scale

_ITEMS = (
    Item("phq9_1", 1, "Little interest or pleasure in doing things"),
    Item("phq9_2", 2, "Feeling down, depressed, or hopeless"),
    Item("phq9_3", 3, "Trouble falling or staying asleep, or sleeping too much"),
    Item("phq9_4", 4, "Feeling tired or having little energy"),
    Item("phq9_5", 5, "Poor appetite or overeating"),
    Item(
        "phq9_6",
        6,
        "Feeling bad about yourself — or that you are a failure or have let "
        "yourself or your family down",
    ),
    Item(
        "phq9_7",
        7,
        "Trouble concentrating on things, such as reading the newspaper or "
        "watching television",
    ),
    Item(
        "phq9_8",
        8,
        "Moving or speaking so slowly that other people could have noticed? Or "
        "the opposite — being so fidgety or restless that you have been "
        "moving around a lot more than usual",
    ),
    Item(
        "phq9_9",
        9,
        "Thoughts that you would be better off dead or of hurting yourself in "
        "some way",
    ),
    Item("phq9_difficulty", 10, DIFFICULTY_TEXT, scored=False, options=DIFFICULTY_OPTIONS),
)

PHQ9 = Instrument(
    id="phq9",
    version="1.0.0",
    name="Patient Health Questionnaire-9",
    short_name="PHQ-9",
    instructions=(
        "Over the last 2 weeks, how often have you been bothered by any of "
        "the following problems?"
    ),
    options=FREQUENCY_OPTIONS,
    items=_ITEMS,
    scales=(
        Scale(
            id="total",
            label="PHQ-9",
            item_ids=tuple(f"phq9_{n}" for n in range(1, 10)),
            max_score=27,
            bands=(
                Band(0, 4, "None-minimal", 0),
                Band(5, 9, "Mild", 1),
                Band(10, 14, "Moderate", 2),
                Band(15, 19, "Moderately severe", 3),
                Band(20, 27, "Severe", 4),
            ),
            # SRS 4.1.3: PHQ-9 >= 10 (Moderate or above).
            referral_min_level=2,
        ),
    ),
    risk_item_rules=(
        # Decision S-D-005 (pending founder sign-off, F1): any non-zero answer
        # on item 9 alerts the physio regardless of the total.
        RiskItemRule(
            item_id="phq9_9",
            min_value=1,
            reason="PHQ-9 item 9 (thoughts of self-harm) answered above 'Not at all'",
        ),
    ),
    citation=(
        "Kroenke K, Spitzer RL, Williams JB. The PHQ-9: validity of a brief "
        "depression severity measure. J Gen Intern Med. 2001;16(9):606-613."
    ),
    licence_note=(
        "Developed by Drs. Spitzer, Williams, Kroenke and colleagues with an "
        "educational grant from Pfizer Inc. No permission required to "
        "reproduce, translate, display or distribute."
    ),
)
