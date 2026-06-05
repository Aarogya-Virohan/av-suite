"""seed_exercises

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01 11:31:21.551225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import urllib.request
import csv
import io
import uuid
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IMG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQjt8-lmP5pv_uBaGy4WukbX06X-CSfe9uRV0u8gXKgTFBs6sGS4g3lH0GR1FlFywU2ANfB1Y4cnoS2/pub?gid=0&single=true&output=csv"
INS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQjt8-lmP5pv_uBaGy4WukbX06X-CSfe9uRV0u8gXKgTFBs6sGS4g3lH0GR1FlFywU2ANfB1Y4cnoS2/pub?gid=606613161&single=true&output=csv"

def upgrade() -> None:
    # Fetch instructions
    ins_req = urllib.request.urlopen(INS_URL)
    ins_data = ins_req.read().decode('utf-8')
    ins_reader = csv.DictReader(io.StringIO(ins_data))
    
    # Fetch images
    img_req = urllib.request.urlopen(IMG_URL)
    img_data = img_req.read().decode('utf-8')
    img_reader = csv.DictReader(io.StringIO(img_data))
    
    images_by_name = {row['Name'].strip().lower(): row['ImageURL'] for row in img_reader if row.get('Name')}
    
    exercises_table = sa.table(
        'exercises',
        sa.column('id', sa.Uuid),
        sa.column('clinic_id', sa.Uuid),
        sa.column('title', sa.String),
        sa.column('description', sa.Text),
        sa.column('body_part', sa.String),
        sa.column('is_free', sa.Boolean),
        sa.column('video_url', sa.String),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )
    
    exercises = []
    now = datetime.now(timezone.utc)
    
    for i, row in enumerate(ins_reader):
        title = row.get('Title', '').strip()
        if not title:
            continue
            
        desc = row.get('Description', '').strip()
        image_url = images_by_name.get(title.lower())
        
        is_free = (i % 3 != 0) # Every 3rd exercise is paid
        
        exercises.append({
            'id': uuid.uuid4(),
            'clinic_id': None,
            'title': title,
            'description': desc,
            'body_part': None,
            'is_free': is_free,
            'video_url': image_url,
            'created_at': now,
            'updated_at': now,
        })
    
    if exercises:
        op.bulk_insert(exercises_table, exercises)


def downgrade() -> None:
    op.execute("DELETE FROM exercises WHERE clinic_id IS NULL")
