"""
Exercise categories: the tag groups and values a library exercise can carry.

Founders' feedback item 1 (23 Oct 2026) asked for 30+ categories. Their
answer to EL-1 (27 Oct): use the same filter groups and category names as
the reference platform the team uses, so we have the same categories; our
exercise content and images are our own. The names below were noted by hand
from that platform's filter panel on 27 Oct 2026 (no data was extracted from
it). An exercise can carry several values, also inside one group.

Order: Joint/Region runs head to toe (founders' item 1, "head to toe as per
joints"); Difficulty runs from easy to hard; "No equipment" comes first in
Equipment; everything else is alphabetical.

Every category id is a uuid5 of "<group>:<name>", so the same category has
the same id on every database. The migration that seeds the table keeps its
own frozen copy of this list; a test checks the two match.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# Namespace for the category ids. Never change it: ids already stored in
# exercise_category_links depend on it.
CATEGORY_NAMESPACE = uuid.UUID("6f1c2b8e-4a7d-5e93-9b1f-0c3d5a7e9f21")

# (key, label), in the order the filter panel shows the groups.
GROUPS: tuple[tuple[str, str], ...] = (
    ("joint_region", "Joint/Region"),
    ("position", "Position"),
    ("movement", "Movement"),
    ("equipment", "Equipment"),
    ("difficulty", "Difficulty"),
    ("specialty", "Specialty"),
    ("objective", "Objective"),
    ("condition", "Condition"),
    ("water_property", "Property of water"),
    ("assistance", "Assistance"),
    ("age_group", "Age group"),
)

VALUES: dict[str, tuple[str, ...]] = {
    "joint_region": (
        "Facial",
        "TMJ",
        "Vestibular",
        "Cervical",
        "Shoulder girdle",
        "Shoulder",
        "Scapula",
        "Arms",
        "Elbow",
        "Wrist",
        "Hand & fingers",
        "Chest",
        "Thoracic",
        "Back",
        "Lumbar",
        "Core & pelvis",
        "Pelvic floor",
        "Hips",
        "Legs",
        "Knee",
        "Above knee amputation",
        "Below knee amputation",
        "Ankle",
        "Foot",
        "Total body",
    ),
    "position": (
        "4 point kneeling",
        "Hanging",
        "Kneeling",
        "Plank/push up",
        "Prone",
        "Side-lying",
        "Single leg stance",
        "Sitting - chair",
        "Sitting - floor",
        "Standing",
        "Supine",
    ),
    "movement": (
        "Abduction",
        "Adduction",
        "Depression",
        "Dorsiflexion",
        "Elevation",
        "Eversion",
        "Extension",
        "Flexion",
        "Inversion",
        "Lateral rotation",
        "Medial rotation",
        "Opposition",
        "Plantar flexion",
        "Pronation",
        "Protraction",
        "Radial deviation",
        "Retraction",
        "Rotation",
        "Scaption",
        "Side flexion",
        "Supination",
        "Ulnar deviation",
    ),
    "equipment": (
        "No equipment",
        "Abdominal roller",
        "Adjustable plinth/bed",
        "Assistant",
        "BOSU ball",
        "Ball - large",
        "Ball - small",
        "Bar",
        "Bar - mobility",
        "Barbell",
        "Bench",
        "Box (plyometric)",
        "Buoyancy collar",
        "Chair",
        "Cones (marker)",
        "Cones (saucer)",
        "Decline board",
        "Defensive mannequin",
        "Devices (respiratory)",
        "Dumbbell",
        "Elbow crutches",
        "Fins",
        "Flip egg",
        "Float - dumbbell",
        "Float - kickboard",
        "Float - noodle",
        "Foam Roller",
        "Foam cube",
        "Hand paddles",
        "Hurdles",
        "Inflatable ring - large",
        "Inflatable ring - small",
        "Inversion table",
        "Jump rope",
        "Kettlebell",
        "Ladder - agility",
        "Ladder - barrel",
        "Machine - cardio",
        "Machine - resistance/weights",
        "Massage cream",
        "Mat",
        "Medicine ball",
        "Mirror",
        "Pilates - reformer",
        "Pillow",
        "Pulley",
        "Resistance band",
        "Rollator frame",
        "Slalom poles",
        "Sliding board",
        "Sliding disc",
        "Sliding sheet",
        "Stability Ball",
        "Step",
        "Stick",
        "Stool",
        "Strap",
        "Suspension straps",
        "Table",
        "Tape",
        "Therabar",
        "Therapy putty",
        "Towel",
        "Toys",
        "Trampoline/trampette",
        "Vibration plate",
        "Wall",
        "Weights, free",
        "Wheelchair",
        "Wobble board",
        "Wobble cushion / foam",
        "Yoga block",
        "Yoga bolster",
    ),
    "difficulty": (
        "Beginner",
        "Intermediate",
        "Advanced",
    ),
    "specialty": (
        "Amputee",
        "Aquatic therapy",
        "Cardiovascular",
        "Education & Daily living",
        "Mental Health",
        "Musculoskeletal (MSK)",
        "Neurology",
        "Occupational Health & Safety",
        "Occupational therapy",
        "Paediatrics",
        "Pilates",
        "Respiratory",
        "Senior health",
        "Speech & Language",
        "Sport",
        "Strength & conditioning",
        "Women's health & pregnancy",
        "Yoga",
    ),
    "objective": (
        "AROM",
        "Acceleration/deceleration",
        "BRRM (modified)",
        "Balance/proprioception",
        "Bone health",
        "Breathlessness management",
        "Cardiovascular",
        "Circulation",
        "Clearing techniques",
        "Functional practice",
        "Gait rehab",
        "Hyperventilation & breathing control",
        "Joint mobilisation",
        "Mindfulness & meditation",
        "Motor skills - fine",
        "Motor skills - gross",
        "Movement preparation/warm-up",
        "Myofascial release",
        "Neural mobilisation",
        "Oedema control",
        "PROM",
        "Perturbation",
        "Plyometrics",
        "Positioning",
        "Postural control",
        "Postural drainage",
        "Relaxation & breathing",
        "Sensation & spatial awareness",
        "Speed & agility",
        "Strength",
        "Strength - bodyweight",
        "Strength - eccentric",
        "Strength - endurance/control",
        "Strength - isometric",
        "Strength - resistance/weighted",
        "Stretch",
        "Stretch - dynamic",
        "Stretch - static",
        "Swallowing",
        "Taping",
        "Tonal management",
        "Traction",
        "Vestibular rehab",
    ),
    "condition": (
        "Incomplete SCI",
        "MS",
        "Other",
        "Parkinsons",
        "SCI C1-C4",
        "SCI C5",
        "SCI C6",
        "SCI C7",
        "SCI L2-S1",
        "SCI T1-L1",
        "Stroke",
        "Vestibular",
    ),
    "water_property": (
        "Buoyancy assisted (BA)",
        "Buoyancy counterbalanced (BC)",
        "Buoyancy resisted (BR)",
        "Drag assisted (DA)",
        "Drag resisted (DR)",
        "Metacentre (MTC)",
        "Turbulence assisted (TA)",
        "Turbulence resisted (TR)",
    ),
    "assistance": (
        "Assisted",
        "Independent",
    ),
    "age_group": (
        "Adult",
        "Child",
        "Infant",
        "Senior",
        "Teen",
    ),
}

GROUP_KEYS: tuple[str, ...] = tuple(key for key, _ in GROUPS)
GROUP_LABELS: dict[str, str] = dict(GROUPS)
GROUP_RANK: dict[str, int] = {key: i for i, key in enumerate(GROUP_KEYS)}


def category_id(group_key: str, name: str) -> uuid.UUID:
    return uuid.uuid5(CATEGORY_NAMESPACE, f"{group_key}:{name}")


@dataclass(frozen=True)
class CategorySeed:
    id: uuid.UUID
    group_key: str
    name: str
    sort_order: int


def seed_rows() -> list[CategorySeed]:
    rows: list[CategorySeed] = []
    for group_key in GROUP_KEYS:
        for i, name in enumerate(VALUES[group_key]):
            rows.append(CategorySeed(category_id(group_key, name), group_key, name, i))
    return rows
