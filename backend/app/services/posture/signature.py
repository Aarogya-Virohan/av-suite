"""
Biomechanical Signature, founders' answer to Q5, 10 October 2026.

The founders removed the single global score and asked for regional
indices shown as a visual profile, with every scan kept as a vector of its
measurements so that scans can later be compared and clustered.

This module adds no clinical judgement. It does not combine parameters
into a new number: how a regional index should be calculated was never
given, and inventing a formula would repeat the global score's problem at a
smaller scale. Each parameter keeps the grade the founders' bands gave it,
and a region shows the worst of its grades. Whether "worst grade" is the
right regional index, and how to show the thoracic region, which has no
parameter, are open founder questions (CURRENT_STATE.md, section 3).
"""

from typing import Any

from app.services.posture.classifier import SEVERITY_LABELS

# Head to toe. Thoracic is listed so the profile shows that the region was
# not measured rather than leaving it out silently: thoracic kyphosis needs
# spinal landmarks the pose model does not return (known_limitations.md,
# PT-L02).
REGIONS: list[tuple[str, str]] = [
    ("head_neck", "Head & Neck"),
    ("shoulders", "Shoulders"),
    ("thoracic", "Thoracic"),
    ("trunk", "Trunk"),
    ("pelvis", "Pelvis"),
    ("knees", "Knees"),
]

REGION_OF: dict[str, str] = {
    "PT-L01": "head_neck",  # Forward Head (CVA), side
    "PT-A01": "head_neck",  # Head Lateral Tilt, front
    "PT-P02": "shoulders",  # Shoulder Level Asymmetry, back
    "PT-P01": "trunk",      # Trunk Lateral Deviation, back
    "PT-L05": "trunk",      # Trunk Lean, side
    "PT-A04": "pelvis",     # Pelvic Obliquity, front
    "PT-A05": "knees",      # Knee Alignment (Hip-Knee-Ankle), front
    "PT-A06": "knees",      # Knee Alignment (Hip-Knee-Ankle), front
    "PT-L06": "knees",      # Knee, side
}

TIER: dict[str, int] = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
SEVERITY_OF_TIER: dict[int, str] = {v: k for k, v in TIER.items()}


def build_signature(views: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    views: {"side": view, "front": view, "back": view}, each with the
    "measurements" list the report already carries.

    Returns {"regions": [...]} in REGIONS order. Each parameter carries its
    grade as a tier, 0 normal to 3 severe, or None when it was not measured,
    so a missing measurement can never read as normal.
    """

    by_region: dict[str, list[dict[str, Any]]] = {rid: [] for rid, _ in REGIONS}

    for view_name in ("side", "front", "back"):
        for m in (views.get(view_name) or {}).get("measurements") or []:
            region = REGION_OF.get(m.get("paramId"))
            if region is None:
                continue
            severity = m.get("severity")
            by_region[region].append(
                {
                    "paramId": m.get("paramId"),
                    "label": m.get("label"),
                    "view": view_name,
                    "severity": severity,
                    "tier": TIER.get(severity),
                    "value": m.get("value"),
                    "unit": m.get("unit"),
                }
            )

    regions = []
    for rid, label in REGIONS:
        params = by_region[rid]
        tiers = [p["tier"] for p in params if p["tier"] is not None]
        worst = SEVERITY_OF_TIER[max(tiers)] if tiers else None
        regions.append(
            {
                "id": rid,
                "label": label,
                "worst": worst,
                # Same wording as the row badges, so no surface keeps its
                # own copy of the labels.
                "worstLabel": SEVERITY_LABELS[worst] if worst else None,
                "measured": len(tiers),
                "parameters": params,
            }
        )

    return {"regions": regions}
