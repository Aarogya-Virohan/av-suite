"""seed_exercises

Revision ID: 22021104ec07
Revises: 0001
Create Date: 2026-06-12 11:43:59.457085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22021104ec07'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import urllib.request
import csv
import io
import uuid
from datetime import datetime

# Helper function to fetch and parse CSV from URL
def fetch_csv(url):
    try:
        response = urllib.request.urlopen(url, timeout=10)
        csv_data = response.read().decode('utf-8')
        reader = csv.reader(io.StringIO(csv_data))
        headers = next(reader)
        rows = list(reader)
        return rows
    except Exception as e:
        print(f"Error fetching CSV from {url}: {e}")
        return []

def upgrade() -> None:
    # Google Sheets URLs
    inst_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQjt8-lmP5pv_uBaGy4WukbX06X-CSfe9uRV0u8gXKgTFBs6sGS4g3lH0GR1FlFywU2ANfB1Y4cnoS2/pub?gid=606613161&single=true&output=csv"
    img_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQjt8-lmP5pv_uBaGy4WukbX06X-CSfe9uRV0u8gXKgTFBs6sGS4g3lH0GR1FlFywU2ANfB1Y4cnoS2/pub?gid=0&single=true&output=csv"

    inst_rows = fetch_csv(inst_url)
    img_rows = fetch_csv(img_url)

    if not inst_rows:
        print("Warning: No instruction rows fetched. Seeding skipped.")
        return

    # Normalize name keys for matching
    def clean(text):
        return text.strip().lower().replace("-", " ")

    # Build image lookup map
    image_map = {}
    for row in img_rows:
        if len(row) >= 2:
            name_clean = clean(row[0])
            image_map[name_clean] = row[1]

    # Manual mapping for items that don't match exactly by clean()
    manual_image_map = {
        "glute squeeze": "glutes",
    }

    # Body parts mapping based on anatomical classification
    body_parts_map = {
        "wall push ups": "Chest",
        "bridging": "Hip",
        "glute squeeze": "Glutes",
        "chin tucks": "Neck",
        "biceps curls": "Arms",
        "neck side stretch": "Neck",
        "pendulum exercise": "Shoulder",
        "wall slides": "Shoulder",
        "scapular squeezes": "Upper Back",
        "cat cow stretch": "Spine",
        "cervical flexion isometrics (front press)": "Neck",
        "cervical  extension isometrics  (back press)": "Neck",
        " lateral flexion  isometric  – right side": "Neck",
    }

    # Connect to the exercises table metadata
    exercises_table = sa.table(
        'exercises',
        sa.column('id', sa.Uuid),
        sa.column('clinic_id', sa.Uuid),
        sa.column('title', sa.String),
        sa.column('description', sa.Text),
        sa.column('body_part', sa.String),
        sa.column('is_free', sa.Boolean),
        sa.column('video_url', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    seed_data = []
    now = datetime.utcnow()

    # Define paid tier exercises to showcase locking functionality in frontend
    paid_exercises = {
        "bridging",
        "pendulum exercise",
        "cervical flexion isometrics (front press)",
        "cervical  extension isometrics  (back press)",
    }

    for row in inst_rows:
        if not row or len(row) < 2:
            continue
        title = row[0].strip()
        description = row[1].strip()
        
        # Skip dummy/test rows
        if title.lower() == "test":
            continue

        title_clean = clean(title)

        # Get matching image URL
        image_key = title_clean
        if title_clean in manual_image_map:
            image_key = clean(manual_image_map[title_clean])
        
        image_url = image_map.get(image_key)

        body_part = body_parts_map.get(title_clean, "Other")
        is_free = title_clean not in paid_exercises

        seed_data.append({
            "id": uuid.uuid4(),
            "clinic_id": None,
            "title": title,
            "description": description,
            "body_part": body_part,
            "is_free": is_free,
            "video_url": image_url, # Store image URL in video_url column
            "created_at": now,
            "updated_at": now
        })

    if seed_data:
        op.bulk_insert(exercises_table, seed_data)
        print(f"Successfully seeded {len(seed_data)} global exercises.")

def downgrade() -> None:
    # Delete all global exercises seeded
    op.execute("DELETE FROM exercises WHERE clinic_id IS NULL")

