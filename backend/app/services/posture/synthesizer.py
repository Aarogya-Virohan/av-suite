"""
Maps clinical findings (param_id -> severity) to muscle imbalance
synthesis: hypertonic (tight/overactive) muscles and inhibited (weak)
muscles.

No exercises since 11 October 2026. The founders (answer 1b) removed the
exercise column from the automated report: the tool flags a deviation and
the physiotherapist prescribes. The exercise and dosage list that used to
sit in each rule below is in git history before that date.

Only findings classified as "moderate" or "severe" trigger a rule —
mild/none findings are not actionable enough to drive corrective work.
"""

from typing import Any


SYNTHESIS_RULES: list[dict[str, Any]] = [
    {
        # PT-L01 — Forward Head Posture (CVA)
        "param_id": "PT-L01",
        "hypertonic": ["Upper Trapezius", "Levator Scapulae", "Sternocleidomastoid"],
        "inhibited": ["Deep Neck Flexors", "Lower Trapezius"],
    },
    {
        # PT-L05 — Forward Trunk Lean
        "param_id": "PT-L05",
        "hypertonic": ["Hip Flexors", "Erector Spinae"],
        "inhibited": ["Gluteus Maximus", "Abdominals"],
    },
    {
        # PT-A01 — Head Lateral Tilt
        "param_id": "PT-A01",
        "hypertonic": ["Upper Trapezius", "Scalenes"],
        "inhibited": ["Deep Neck Flexors", "Lower Trapezius"],
    },
    # PT-A02 and PT-A03 left the front view on 10 October 2026; the same
    # quantities are now reported only as PT-P02 and PT-P01. Their mappings
    # moved with the quantity, see those entries.
    {
        # PT-A04 — Pelvic Obliquity
        "param_id": "PT-A04",
        "hypertonic": ["Quadratus Lumborum"],
        "inhibited": ["Gluteus Medius"],
    },
    {
        # PT-A05 — Knee Valgus
        "param_id": "PT-A05",
        "hypertonic": ["Adductors", "IT Band / TFL"],
        "inhibited": ["Gluteus Medius", "VMO"],
    },
    {
        # PT-A06 — Knee Varus
        "param_id": "PT-A06",
        "hypertonic": ["IT Band / TFL"],
        "inhibited": ["Adductors"],
    },
    # PT-A10 (Ear Level Asymmetry) removed 11 October 2026 with the row.
    {
        # PT-P01 — Trunk Lateral Deviation (Posterior). FOR REVIEW.
        # Since 10 October 2026 this carries the mapping written for the
        # same quantity on the front view (PT-A03, trunk lateral shift). The
        # previous mapping here was written when the row was "Scoliosis
        # Screen" (one-sided erector spinae, Schroth breathing); the row has
        # made no scoliosis claim since 18 Sept.
        "param_id": "PT-P01",
        "hypertonic": ["Quadratus Lumborum", "Obliques (one side)"],
        "inhibited": ["Gluteus Medius"],
    },
    {
        # PT-P02 — Shoulder Level Asymmetry. FOR REVIEW.
        # Since 10 October 2026 this carries the mapping written for the
        # same quantity on the front view (PT-A02). The previous mapping here
        # (serratus anterior, wall slides) was written for scapular winging,
        # which a 2D photograph cannot detect and this row does not claim.
        "param_id": "PT-P02",
        "hypertonic": ["Upper Trapezius"],
        "inhibited": ["Middle Trapezius"],
    },
    # PT-P03 and PT-P05 had entries here. Both parameters were withdrawn
    # from the report on 1 October 2026, so their muscle and exercise
    # mappings are removed with them. PT-P04 was withdrawn the same way on
    # 2 October 2026 and its entry is removed for the same reason: a
    # mapping fires on a grade that no longer exists.
    # See docs/known_limitations.md.
    {
        # PT-L06 — Knee Hyperextension (Genu Recurvatum)
        "param_id": "PT-L06",
        "hypertonic": ["Gastrocnemius", "Soleus"],
        "inhibited": ["Quadriceps", "Hamstrings"],
    },
    # PT-A08 had an entry here. The parameter was withdrawn from the
    # report on 2 October 2026, so its muscle and exercise mapping is
    # removed with it. See docs/known_limitations.md.
]


TRIGGER_SEVERITIES = {"moderate", "severe"}


def generate_synthesis(findings: dict[str, str]) -> dict[str, Any]:

    hypertonic: set[str] = set()
    inhibited: set[str] = set()

    for finding_key, severity in findings.items():

        if severity not in TRIGGER_SEVERITIES:
            continue

        # Bilateral/sub-classified findings are keyed e.g.
        # "PT-A05_left" / "PT-A06_right", or potentially
        # "<param>_<subtype>_<side>" for future multi-part keys. The
        # base param id is everything except the trailing side suffix;
        # for keys with no underscore at all, the whole key is the base.
        parts = finding_key.split("_")

        if len(parts) == 1:
            base_param_id = parts[0]
        else:
            base_param_id = "_".join(parts[:-1])

        for rule in SYNTHESIS_RULES:

            if rule["param_id"] != base_param_id:
                continue

            hypertonic.update(rule["hypertonic"])
            inhibited.update(rule["inhibited"])

    return {
        "hypertonic": sorted(hypertonic),
        "inhibited": sorted(inhibited),
    }
