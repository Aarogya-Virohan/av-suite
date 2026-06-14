"""
Maps clinical findings (param_id -> severity) to muscle imbalance
synthesis: hypertonic (tight/overactive) muscles, inhibited (weak)
muscles, and a corrective exercise protocol.

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
        "corrective": [
            {"exercise": "Chin Tucks", "dosage": "3x12"},
            {"exercise": "Wall Slides", "dosage": "3x10"},
        ],
    },
    {
        # PT-L05 — Forward Trunk Lean
        "param_id": "PT-L05",
        "hypertonic": ["Hip Flexors", "Erector Spinae"],
        "inhibited": ["Gluteus Maximus", "Abdominals"],
        "corrective": [
            {"exercise": "Hip Flexor Stretch", "dosage": "3x30s each side"},
        ],
    },
    {
        # PT-A01 — Head Lateral Tilt
        "param_id": "PT-A01",
        "hypertonic": ["Upper Trapezius", "Scalenes"],
        "inhibited": ["Deep Neck Flexors", "Lower Trapezius"],
        "corrective": [
            {"exercise": "Lateral Neck Stretch", "dosage": "3x30s each side"},
        ],
    },
    {
        # PT-A02 — Shoulder Level Asymmetry
        "param_id": "PT-A02",
        "hypertonic": ["Upper Trapezius"],
        "inhibited": ["Middle Trapezius"],
        "corrective": [
            {"exercise": "Scapular Retraction", "dosage": "3x15"},
        ],
    },
    {
        # PT-A03 — Trunk Lateral Shift
        "param_id": "PT-A03",
        "hypertonic": ["Quadratus Lumborum", "Obliques (one side)"],
        "inhibited": ["Gluteus Medius"],
        "corrective": [
            {"exercise": "Side Plank", "dosage": "3x20s each side"},
        ],
    },
    {
        # PT-A04 — Pelvic Obliquity
        "param_id": "PT-A04",
        "hypertonic": ["Quadratus Lumborum"],
        "inhibited": ["Gluteus Medius"],
        "corrective": [
            {"exercise": "Side-Lying Hip Abduction", "dosage": "3x15 each side"},
        ],
    },
    {
        # PT-A05 — Knee Valgus
        "param_id": "PT-A05",
        "hypertonic": ["Adductors", "IT Band / TFL"],
        "inhibited": ["Gluteus Medius", "VMO"],
        "corrective": [
            {"exercise": "Clamshells", "dosage": "3x15 each side"},
        ],
    },
    {
        # PT-A06 — Knee Varus
        "param_id": "PT-A06",
        "hypertonic": ["IT Band / TFL"],
        "inhibited": ["Adductors"],
        "corrective": [
            {"exercise": "Adductor Strengthening", "dosage": "3x15"},
        ],
    },
    {
        # PT-A10 — Ear Level Asymmetry
        "param_id": "PT-A10",
        "hypertonic": ["Sternocleidomastoid", "Upper Trapezius"],
        "inhibited": ["Deep Neck Flexors"],
        "corrective": [
            {"exercise": "Cervical Side-Bend Stretch", "dosage": "3x10 each side"},
        ],
    },
    {
        # PT-P01 — Scoliosis Screen
        "param_id": "PT-P01",
        "hypertonic": ["Quadratus Lumborum", "Erector Spinae (one side)"],
        "inhibited": ["Obliques", "Gluteus Medius"],
        "corrective": [
            {"exercise": "Schroth Method Breathing", "dosage": "Daily 15 min"},
        ],
    },
    {
        # PT-P02 — Scapular Asymmetry (Winging / Height)
        "param_id": "PT-P02",
        "hypertonic": ["Levator Scapulae", "Upper Trapezius"],
        "inhibited": ["Serratus Anterior", "Lower Trapezius"],
        "corrective": [
            {"exercise": "Scapular Wall Slides", "dosage": "3x12"},
        ],
    },
    {
        # PT-P03 — Heel Valgus / Subtalar Alignment
        "param_id": "PT-P03",
        "hypertonic": ["Peroneals"],
        "inhibited": ["Tibialis Posterior"],
        "corrective": [
            {"exercise": "Heel Raises with Inward Press", "dosage": "3x15"},
        ],
    },
    {
        # PT-P04 — Pelvic Rotation (Axial)
        "param_id": "PT-P04",
        "hypertonic": ["Piriformis"],
        "inhibited": ["Gluteus Medius", "Deep Core Stabilisers"],
        "corrective": [
            {"exercise": "Pelvic Rotation Control Drills", "dosage": "3x10 each side"},
        ],
    },
    {
        # PT-P05 — Bilateral Toe Angle Asymmetry
        "param_id": "PT-P05",
        "hypertonic": ["Piriformis (one side)"],
        "inhibited": ["Hip Internal Rotators"],
        "corrective": [
            {"exercise": "Hip Internal/External Rotation Stretch", "dosage": "3x30s each side"},
        ],
    },
    {
        # PT-L06 — Knee Hyperextension (Genu Recurvatum)
        "param_id": "PT-L06",
        "hypertonic": ["Gastrocnemius", "Soleus"],
        "inhibited": ["Quadriceps", "Hamstrings"],
        "corrective": [
            {"exercise": "Terminal Knee Extension Control", "dosage": "3x15"},
        ],
    },
    {
        # PT-A08 — Elbow Carrying Angle
        # Low clinical confidence (geometric approximation) — flagged
        # for clinician review; kept generic until validated.
        "param_id": "PT-A08",
        "hypertonic": ["Forearm Flexors"],
        "inhibited": ["Forearm Extensors"],
        "corrective": [
            {"exercise": "Forearm Stretch & Strengthen", "dosage": "3x15"},
        ],
    },
]


TRIGGER_SEVERITIES = {"moderate", "severe"}


def generate_synthesis(findings: dict[str, str]) -> dict[str, Any]:

    hypertonic: set[str] = set()
    inhibited: set[str] = set()

    corrective: list[dict[str, str]] = []
    seen_exercises: set[str] = set()

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

            for exercise in rule["corrective"]:

                if exercise["exercise"] in seen_exercises:
                    continue

                seen_exercises.add(exercise["exercise"])
                corrective.append(exercise)

    return {
        "hypertonic": sorted(hypertonic),
        "inhibited": sorted(inhibited),
        "correctiveProtocol": corrective,
    }
