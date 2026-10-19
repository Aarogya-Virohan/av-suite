"""Response options shared by PHQ-9 and GAD-7 (identical on both published forms)."""

from app.screening.types import ResponseOption

FREQUENCY_OPTIONS = (
    ResponseOption(0, "Not at all"),
    ResponseOption(1, "Several days"),
    ResponseOption(2, "More than half the days"),
    ResponseOption(3, "Nearly every day"),
)

# Functional-impairment question that closes both published forms. It is not
# part of the score; it is recorded for the physio's context only.
DIFFICULTY_TEXT = (
    "If you checked off any problems, how difficult have these problems made "
    "it for you to do your work, take care of things at home, or get along "
    "with other people?"
)

DIFFICULTY_OPTIONS = (
    ResponseOption(0, "Not difficult at all"),
    ResponseOption(1, "Somewhat difficult"),
    ResponseOption(2, "Very difficult"),
    ResponseOption(3, "Extremely difficult"),
)
