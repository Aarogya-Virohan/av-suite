"""
Exercise Library structure: 9 domains and 51 categories (EL-D-012).

Source: Shivank sir's exercise bank workbook, sheet "Final Categories"
(founders' structure, final per Onkar 19 Nov 2026). Stored as two more tag
groups in exercise_categories ("domain", "category"), next to the 11 filter
groups of EL-D-005, so no new table is needed. Every category belongs to one
domain; the filter panel uses that to show only the picked domain's
categories.

Ids follow the EL-D-005 rule: uuid5("<group>:<name>") in the same namespace,
so they are the same on every database. Revision e7c3a9f1b5d2 seeds the rows
from its own frozen copy; a test checks the two match.

Also here: how an exercise may be used on a home prescription (rx_mode,
plan C1) and which exercises need the therapist to pick a side (plan C2).
"""

from __future__ import annotations

import uuid

from app.services.exercise_categories import CATEGORY_NAMESPACE

STRUCTURE_GROUPS: tuple[tuple[str, str], ...] = (
    ("domain", "Domain"),
    ("category", "Category"),
)

# Domain -> its categories, in the workbook's order.
DOMAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Mobility & Flexibility", (
        "Facial & TMJ", "Neural mobility", "Range of motion", "Self-mobilisation", "Stretching",
        "Workplace micro-breaks",
    )),
    ("Strength & Power", (
        "Bodyweight", "Elastic resistance", "Free weights", "Machines & cable", "Medicine ball & suspension",
        "Power & agility",
    )),
    ("Neuromuscular Control", ("Mat activities", "Motor control & core", "PNF patterns", "Proprioception")),
    ("Balance, Posture & Vestibular", (
        "Dynamic balance", "Falls prevention", "Postural correction", "Reactive balance", "Static balance",
        "Vestibular rehabilitation",
    )),
    ("Functional, Gait & ADL", (
        "ADL & task practice", "Bed-level & early mobilisation", "Gait training", "Gym ball & apparatus",
        "Hand & fine motor", "Transfers & wheelchair skills", "Work & sport tasks",
    )),
    ("Aerobic & Endurance", (
        "Aquatic", "Arm and seated", "Circuit", "Cycling", "Stepping and low-impact", "Supported gait",
        "Walking", "Warm-up and cool-down",
    )),
    ("Respiratory & Breathing", (
        "Airway clearance", "Breathing control", "Inspiratory muscle training", "Lung expansion",
        "Positioning for breathlessness",
    )),
    ("Mind-body & Pain Management", ("Graded activity & exposure", "Pacing", "Relaxation", "Therapeutic yoga")),
    ("Therapist-applied Techniques", (
        "Joint mobilisation", "PNF techniques", "Positioning & splinting", "Soft tissue & MET", "Taping",
    )),
)

DOMAIN_NAMES: tuple[str, ...] = tuple(d for d, _ in DOMAINS)
CATEGORY_NAMES: tuple[str, ...] = tuple(c for _, cats in DOMAINS for c in cats)


def structure_id(group_key: str, name: str) -> uuid.UUID:
    return uuid.uuid5(CATEGORY_NAMESPACE, f"{group_key}:{name}")


# category id -> domain id, for the cascading filter.
CATEGORY_PARENT: dict[uuid.UUID, uuid.UUID] = {
    structure_id("category", c): structure_id("domain", d) for d, cats in DOMAINS for c in cats
}


def seed_rows() -> list[tuple[uuid.UUID, str, str, int]]:
    """(id, group_key, name, sort_order) for the two structure groups."""
    rows = [(structure_id("domain", d), "domain", d, i) for i, d in enumerate(DOMAIN_NAMES)]
    rows += [(structure_id("category", c), "category", c, i) for i, c in enumerate(CATEGORY_NAMES)]
    return rows


# ---------------------------------------------------------------- Rx rules

RX_PATIENT = "PATIENT"
RX_CAREGIVER = "CAREGIVER"
RX_BLOCKED = "BLOCKED"
# Not listed, not searchable, not prescribable; the row stays for old Rx and
# templates (EL-D-017: "(seated)" copies that cannot be done seated).
RX_HIDDEN = "HIDDEN"
RX_MODES = (RX_PATIENT, RX_CAREGIVER, RX_BLOCKED, RX_HIDDEN)

SIDES = ("left", "right")

# Label printed on the PDF and shown in the app for caregiver items.
CAREGIVER_LABEL = "Caregiver-assisted"
