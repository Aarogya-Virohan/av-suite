"""seed_test_matrix

Revision ID: 5045c801bd96
Revises: 17720d35ae64
Create Date: 2026-06-12 12:38:55.038689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5045c801bd96'
down_revision: Union[str, Sequence[str], None] = '17720d35ae64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import uuid
from datetime import datetime, date
from app.core.security import get_password_hash

def upgrade() -> None:
    # 1. Clean up existing data to start fresh
    op.execute("DELETE FROM prescription_items")
    op.execute("DELETE FROM prescriptions")
    op.execute("DELETE FROM posture_measurements")
    op.execute("DELETE FROM posture_sessions")
    op.execute("DELETE FROM exercises")
    op.execute("DELETE FROM patients")
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM clinics")

    # Table descriptors
    clinics_table = sa.table(
        'clinics',
        sa.column('id', sa.Uuid),
        sa.column('name', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )

    users_table = sa.table(
        'users',
        sa.column('id', sa.Uuid),
        sa.column('clinic_id', sa.Uuid),
        sa.column('email', sa.String),
        sa.column('password_hash', sa.String),
        sa.column('role', sa.Enum('admin', 'physio', 'patient', name='userrole')),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )

    patients_table = sa.table(
        'patients',
        sa.column('id', sa.Uuid),
        sa.column('clinic_id', sa.Uuid),
        sa.column('user_id', sa.Uuid),
        sa.column('first_name', sa.String),
        sa.column('last_name', sa.String),
        sa.column('date_of_birth', sa.Date),
        sa.column('phone', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )

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
        sa.column('updated_at', sa.DateTime)
    )

    now = datetime.utcnow()
    hashed_pwd = get_password_hash("password123")

    # IDs definitions
    c1 = uuid.UUID("c1111111-1111-1111-1111-111111111111")
    c2 = uuid.UUID("c2222222-2222-2222-2222-222222222222")
    c3 = uuid.UUID("c3333333-3333-3333-3333-333333333333")

    u1 = uuid.UUID("d1111111-1111-1111-1111-111111111111")
    u2 = uuid.UUID("d2222222-2222-2222-2222-222222222222")
    u3 = uuid.UUID("d3333333-3333-3333-3333-333333333333")

    # 1. Insert Clinics
    clinics_data = [
        {"id": c1, "name": "Aarogya-Virohan Central Clinic", "created_at": now, "updated_at": now},
        {"id": c2, "name": "Care & Recovery Clinic", "created_at": now, "updated_at": now},
        {"id": c3, "name": "Apex Physical Therapy", "created_at": now, "updated_at": now}
    ]
    op.bulk_insert(clinics_table, clinics_data)

    # 2. Insert Admin Users
    users_data = [
        {"id": u1, "clinic_id": c1, "email": "admin1@avsuite.com", "password_hash": hashed_pwd, "role": "admin", "created_at": now, "updated_at": now},
        {"id": u2, "clinic_id": c2, "email": "admin2@avsuite.com", "password_hash": hashed_pwd, "role": "admin", "created_at": now, "updated_at": now},
        {"id": u3, "clinic_id": c3, "email": "admin3@avsuite.com", "password_hash": hashed_pwd, "role": "admin", "created_at": now, "updated_at": now}
    ]
    op.bulk_insert(users_table, users_data)

    # 3. Insert Patients
    patients_data = [
        # Clinic 1 Patients
        {"id": uuid.UUID("a1111111-1111-1111-1111-111111111111"), "clinic_id": c1, "user_id": None, "first_name": "Ramesh", "last_name": "Kumar", "date_of_birth": date(1985, 5, 15), "phone": "9876543210", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("a1111111-1111-1111-1111-222222222222"), "clinic_id": c1, "user_id": None, "first_name": "Sunita", "last_name": "Sharma", "date_of_birth": date(1990, 8, 22), "phone": "9876543211", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("a1111111-1111-1111-1111-333333333333"), "clinic_id": c1, "user_id": None, "first_name": "Amit", "last_name": "Patel", "date_of_birth": date(1978, 12, 1), "phone": "9876543212", "created_at": now, "updated_at": now},
        # Clinic 2 Patients
        {"id": uuid.UUID("b2222222-2222-2222-2222-111111111111"), "clinic_id": c2, "user_id": None, "first_name": "David", "last_name": "Miller", "date_of_birth": date(1982, 3, 10), "phone": "9876543220", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("b2222222-2222-2222-2222-222222222222"), "clinic_id": c2, "user_id": None, "first_name": "Sarah", "last_name": "Connor", "date_of_birth": date(1989, 11, 25), "phone": "9876543221", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("b2222222-2222-2222-2222-333333333333"), "clinic_id": c2, "user_id": None, "first_name": "John", "last_name": "Smith", "date_of_birth": date(1995, 7, 14), "phone": "9876543222", "created_at": now, "updated_at": now},
        # Clinic 3 Patients
        {"id": uuid.UUID("f3333333-3333-3333-3333-111111111111"), "clinic_id": c3, "user_id": None, "first_name": "Priya", "last_name": "Nair", "date_of_birth": date(1987, 9, 5), "phone": "9876543230", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("f3333333-3333-3333-3333-222222222222"), "clinic_id": c3, "user_id": None, "first_name": "Vikram", "last_name": "Singh", "date_of_birth": date(1980, 4, 18), "phone": "9876543231", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("f3333333-3333-3333-3333-333333333333"), "clinic_id": c3, "user_id": None, "first_name": "Neha", "last_name": "Gupta", "date_of_birth": date(1992, 1, 30), "phone": "9876543232", "created_at": now, "updated_at": now}
    ]
    op.bulk_insert(patients_table, patients_data)

    # 4. Insert Exercises
    exercises_data = [
        # Clinic 1 specific
        {"id": uuid.UUID("e1111111-1111-1111-1111-111111111111"), "clinic_id": c1, "title": "C1 Shoulder External Rotation", "description": "Focus on slow, controlled rotation using a resistance band.", "body_part": "Shoulder", "is_free": True, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEg-w49qaZjspvJDbaoPEvrPxhDjz0o8y8uLvqHj0zgoMh2nqTrsRiZjbMrOeFzUA4Wob5AEyRlZQr5cnM2VjwhsC0BJ-xOyJdL0W99KgTSgogcLGP_L2x1HhrHMtlrBNgWB86zMUIPuXdxLdq9Y-Bt4gOA7SGJnXBSRr4I62d_zsq7Ha5N8SKUijNajKjsV", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e1111111-1111-1111-1111-222222222222"), "clinic_id": c1, "title": "C1 Active Ankle Dorsiflexion", "description": "Pull toes up towards the shin, hold, and return.", "body_part": "Ankle", "is_free": True, "video_url": "", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e1111111-1111-1111-1111-333333333333"), "clinic_id": c1, "title": "C1 Wrist Extension Stretch", "description": "Gently pull fingers back to stretch the forearm flexors.", "body_part": "Wrist", "is_free": False, "video_url": "", "created_at": now, "updated_at": now},
        
        # Clinic 2 specific
        {"id": uuid.UUID("e2222222-2222-2222-2222-111111111111"), "clinic_id": c2, "title": "C2 Prone Hip Extension", "description": "Lift thigh off the table keeping knee straight.", "body_part": "Hip", "is_free": True, "video_url": "", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e2222222-2222-2222-2222-222222222222"), "clinic_id": c2, "title": "C2 Quadriceps Setting", "description": "Tighten thigh muscle, pushing back of knee down.", "body_part": "Knee", "is_free": True, "video_url": "", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e2222222-2222-2222-2222-333333333333"), "clinic_id": c2, "title": "C2 Hamstring Stretch", "description": "Lie down, lift leg using a strap to stretch the back of the thigh.", "body_part": "Hamstring", "is_free": False, "video_url": "", "created_at": now, "updated_at": now},
        
        # Clinic 3 specific
        {"id": uuid.UUID("e3333333-3333-3333-3333-111111111111"), "clinic_id": c3, "title": "C3 Cervical Range of Motion", "description": "Gently turn head left and right to pain-free limits.", "body_part": "Neck", "is_free": True, "video_url": "", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e3333333-3333-3333-3333-222222222222"), "clinic_id": c3, "title": "C3 Thoracic Extension on Foam Roller", "description": "Support neck, arch upper back over the roller.", "body_part": "Spine", "is_free": True, "video_url": "", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e3333333-3333-3333-3333-333333333333"), "clinic_id": c3, "title": "C3 Abdominal Drawing-in", "description": "Pull belly button in toward spine while breathing normally.", "body_part": "Spine", "is_free": False, "video_url": "", "created_at": now, "updated_at": now},
        
        # 5 Global Exercises (no clinic_id)
        {"id": uuid.UUID("e0000000-0000-0000-0000-111111111111"), "clinic_id": None, "title": "Chin Tucks", "description": "Draw head straight back making a double chin, eyes level.", "body_part": "Neck", "is_free": True, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEijwrhWkQSFbpb201MDQHdMDBiqOmnG3LlIpN0LxhsCluPUtRJNGYWKenRgvLK3o--8D_3_oJh2P-2mg3kEx5HwqPTExvUMknI2HzS_hwveirnp6XHqoSpJEU65fqMsTmr523J1PHhNel5QOAWNk4EaizjWxBQiqSQp_qb6zrYt0H2j0gADZ2kXNLIz2u4B", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e0000000-0000-0000-0000-222222222222"), "clinic_id": None, "title": "Wall slides", "description": "Slide arms up and down a wall in a goalpost position.", "body_part": "Shoulder", "is_free": True, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEiXyQqyUnMDhlBoAikvc2F-zSE1-IJbd4fs8t1fL6DiyBlJFaTQEwL0tHMop05JeSEQrtIYvNRMg1SJYPH5DmAqvt5MkSpPVb48NeCag1NoXVHVPN6-I-l0ZYzSzIBgka7KOMXAP-Np0hnicDwtnrf_RCop-LsNmpdgaKPAGmqeXmgD-Pj5ppbnly5TIhDq", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e0000000-0000-0000-0000-333333333333"), "clinic_id": None, "title": "Scapular squeezes", "description": "Squeeze shoulder blades together as if holding a pencil.", "body_part": "Upper Back", "is_free": True, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEg7iekspghjCYWg7W9iD22-iz78xYTHJ7B5Z1cKS_f0e6P-hITOY5MioFGrIrtsusY2qvB0OUMBHbSNSA8mafoLashDN78S5PRF-rowf0_8RJM35On-mLh8uLLaKlGoR1p3y8ALWbzEoMkevc3IN87o3hyDK7OupJqBCy7s7-_sC50j8Nb7XXn2k-G3VnrH=w421-h421", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e0000000-0000-0000-0000-444444444444"), "clinic_id": None, "title": "Bridging", "description": "Lie on back, bend knees, lift hips to form straight line.", "body_part": "Hip", "is_free": False, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEiH_5zxH7e8nGfRs7k_EZUkoOJqsCgutIMsKD2LzydGi3QmGTJ_BkFHV6yfmpYnkaMozdoYWrsCkfvJBWbnzGrXhfxZrF5gbMv3RUO40chf6kV466IGwjWTNFqKuEUEyUAtpmCAm0Jev5OUWx1OPcJzTEjcTgll0Wqwc_F3mgPcYo3jl5vnh5Xhr41lkvMO", "created_at": now, "updated_at": now},
        {"id": uuid.UUID("e0000000-0000-0000-0000-555555555555"), "clinic_id": None, "title": "Glute Squeeze", "description": "Squeeze buttock muscles tight, hold 5 seconds, relax.", "body_part": "Glutes", "is_free": True, "video_url": "https://blogger.googleusercontent.com/img/a/AVvXsEg7iekspghjCYWg7W9iD22-iz78xYTHJ7B5Z1cKS_f0e6P-hITOY5MioFGrIrtsusY2qvB0OUMBHbSNSA8mafoLashDN78S5PRF-rowf0_8RJM35On-mLh8uLLaKlGoR1p3y8ALWbzEoMkevc3IN87o3hyDK7OupJqBCy7s7-_sC50j8Nb7XXn2k-G3VnrH=w421-h421", "created_at": now, "updated_at": now}
    ]
    op.bulk_insert(exercises_table, exercises_data)

def downgrade() -> None:
    # Delete seeded items
    op.execute("DELETE FROM exercises")
    op.execute("DELETE FROM patients")
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM clinics")

