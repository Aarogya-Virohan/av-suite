"""exercise categories: tag groups and values, and exercise to category links

Revision ID: d2f6a8c0e4b1
Revises: c1e5f7a9b3d2
Create Date: 2026-10-27

Seeds the category list (EL-D-005). The list below is a frozen copy of
app/services/exercise_categories.py as of this revision; later changes to
the list need their own migration. Ids are uuid5("<group>:<name>") in a fixed
namespace, so they are the same on every database.

Note: the open CDSS branch (feat/tool03-psychosocial) chains from
a8c4e2f1d903. Whichever reaches dev second must point its first migration's
down_revision at the other branch's last revision and be tested again.
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "d2f6a8c0e4b1"
down_revision: Union[str, Sequence[str], None] = "c1e5f7a9b3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMESPACE = uuid.UUID("6f1c2b8e-4a7d-5e93-9b1f-0c3d5a7e9f21")

SEED = (
    ('joint_region', (
        'Facial',
        'TMJ',
        'Vestibular',
        'Cervical',
        'Shoulder girdle',
        'Shoulder',
        'Scapula',
        'Arms',
        'Elbow',
        'Wrist',
        'Hand & fingers',
        'Chest',
        'Thoracic',
        'Back',
        'Lumbar',
        'Core & pelvis',
        'Pelvic floor',
        'Hips',
        'Legs',
        'Knee',
        'Above knee amputation',
        'Below knee amputation',
        'Ankle',
        'Foot',
        'Total body',
    )),
    ('position', (
        '4 point kneeling',
        'Hanging',
        'Kneeling',
        'Plank/push up',
        'Prone',
        'Side-lying',
        'Single leg stance',
        'Sitting - chair',
        'Sitting - floor',
        'Standing',
        'Supine',
    )),
    ('movement', (
        'Abduction',
        'Adduction',
        'Depression',
        'Dorsiflexion',
        'Elevation',
        'Eversion',
        'Extension',
        'Flexion',
        'Inversion',
        'Lateral rotation',
        'Medial rotation',
        'Opposition',
        'Plantar flexion',
        'Pronation',
        'Protraction',
        'Radial deviation',
        'Retraction',
        'Rotation',
        'Scaption',
        'Side flexion',
        'Supination',
        'Ulnar deviation',
    )),
    ('equipment', (
        'No equipment',
        'Abdominal roller',
        'Adjustable plinth/bed',
        'Assistant',
        'BOSU ball',
        'Ball - large',
        'Ball - small',
        'Bar',
        'Bar - mobility',
        'Barbell',
        'Bench',
        'Box (plyometric)',
        'Buoyancy collar',
        'Chair',
        'Cones (marker)',
        'Cones (saucer)',
        'Decline board',
        'Defensive mannequin',
        'Devices (respiratory)',
        'Dumbbell',
        'Elbow crutches',
        'Fins',
        'Flip egg',
        'Float - dumbbell',
        'Float - kickboard',
        'Float - noodle',
        'Foam Roller',
        'Foam cube',
        'Hand paddles',
        'Hurdles',
        'Inflatable ring - large',
        'Inflatable ring - small',
        'Inversion table',
        'Jump rope',
        'Kettlebell',
        'Ladder - agility',
        'Ladder - barrel',
        'Machine - cardio',
        'Machine - resistance/weights',
        'Massage cream',
        'Mat',
        'Medicine ball',
        'Mirror',
        'Pilates - reformer',
        'Pillow',
        'Pulley',
        'Resistance band',
        'Rollator frame',
        'Slalom poles',
        'Sliding board',
        'Sliding disc',
        'Sliding sheet',
        'Stability Ball',
        'Step',
        'Stick',
        'Stool',
        'Strap',
        'Suspension straps',
        'Table',
        'Tape',
        'Therabar',
        'Therapy putty',
        'Towel',
        'Toys',
        'Trampoline/trampette',
        'Vibration plate',
        'Wall',
        'Weights, free',
        'Wheelchair',
        'Wobble board',
        'Wobble cushion / foam',
        'Yoga block',
        'Yoga bolster',
    )),
    ('difficulty', (
        'Beginner',
        'Intermediate',
        'Advanced',
    )),
    ('specialty', (
        'Amputee',
        'Aquatic therapy',
        'Cardiovascular',
        'Education & Daily living',
        'Mental Health',
        'Musculoskeletal (MSK)',
        'Neurology',
        'Occupational Health & Safety',
        'Occupational therapy',
        'Paediatrics',
        'Pilates',
        'Respiratory',
        'Senior health',
        'Speech & Language',
        'Sport',
        'Strength & conditioning',
        "Women's health & pregnancy",
        'Yoga',
    )),
    ('objective', (
        'AROM',
        'Acceleration/deceleration',
        'Balance/proprioception',
        'Bone health',
        'Breathlessness management',
        'Cardiovascular',
        'Circulation',
        'Clearing techniques',
        'Functional practice',
        'Gait rehab',
        'Hyperventilation & breathing control',
        'Joint mobilisation',
        'Mindfulness & meditation',
        'Motor skills - fine',
        'Motor skills - gross',
        'Movement preparation/warm-up',
        'Myofascial release',
        'Neural mobilisation',
        'Oedema control',
        'PROM',
        'Perturbation',
        'Plyometrics',
        'Positioning',
        'Postural control',
        'Relaxation & breathing',
        'Sensation & spatial awareness',
        'Speed & agility',
        'Strength',
        'Strength - bodyweight',
        'Strength - eccentric',
        'Strength - endurance/control',
        'Strength - isometric',
        'Strength - resistance/weighted',
        'Stretch',
        'Stretch - dynamic',
        'Stretch - static',
        'Vestibular rehab',
    )),
    ('condition', (
        'Incomplete SCI',
        'MS',
        'Other',
        'Parkinsons',
        'SCI C1-C4',
        'SCI C5',
        'SCI C6',
        'SCI C7',
        'SCI L2-S1',
        'SCI T1-L1',
        'Stroke',
        'Vestibular',
    )),
    ('water_property', (
        'Buoyancy assisted (BA)',
        'Buoyancy counterbalanced (BC)',
        'Buoyancy resisted (BR)',
        'Drag assisted (DA)',
        'Drag resisted (DR)',
        'Metacentre (MTC)',
        'Turbulence assisted (TA)',
        'Turbulence resisted (TR)',
    )),
    ('assistance', (
        'Assisted',
        'Independent',
    )),
    ('age_group', (
        'Adult',
        'Child',
        'Infant',
        'Senior',
        'Teen',
    )),
)


def upgrade() -> None:
    categories = op.create_table(
        "exercise_categories",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("group_key", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("group_key", "name", name="uq_exercise_categories_group_name"),
    )
    op.create_index("ix_exercise_categories_group_key", "exercise_categories", ["group_key"])
    op.create_table(
        "exercise_category_links",
        sa.Column("exercise_id", PGUUID(as_uuid=True), sa.ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", PGUUID(as_uuid=True), sa.ForeignKey("exercise_categories.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_exercise_category_links_category_id", "exercise_category_links", ["category_id"])

    rows = []
    for group_key, names in SEED:
        for order, name in enumerate(names):
            rows.append({
                "id": uuid.uuid5(NAMESPACE, f"{group_key}:{name}"),
                "group_key": group_key,
                "name": name,
                "sort_order": order,
                "is_active": True,
            })
    op.bulk_insert(categories, rows)


def downgrade() -> None:
    op.drop_index("ix_exercise_category_links_category_id", table_name="exercise_category_links")
    op.drop_table("exercise_category_links")
    op.drop_index("ix_exercise_categories_group_key", table_name="exercise_categories")
    op.drop_table("exercise_categories")
