"""seed_exercises

Revision ID: 22021104ec07
Revises: 0001
Create Date: 2026-06-12 11:43:59.457085

NOTE: Rewritten to remove runtime network dependency on Google Sheets.
Real exercise content captured once and baked in below as static data.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime

revision: str = '22021104ec07'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_EXERCISES = [{'id': '705867ae-be84-41bd-a625-414bbeac4e7b', 'title': 'wall push ups', 'description': 'Lean against a wall, slide down into a seated position, hold for 20 seconds, and slide back up.', 'body_part': 'Chest', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEiXyQqyUnMDhlBoAikvc2F-zSE1-IJbd4fs8t1fL6DiyBlJFaTQEwL0tHMop05JeSEQrtIYvNRMg1SJYPH5DmAqvt5MkSpPVb48NeCag1NoXVHVPN6-I-l0ZYzSzIBgka7KOMXAP-Np0hnicDwtnrf_RCop-LsNmpdgaKPAGmqeXmgD-Pj5ppbnly5TIhDq'}, {'id': 'abf1c2d0-cc3e-4034-b293-87c7908b372b', 'title': 'bridging', 'description': 'Lie on your back with knees bent, squeeze your glutes to lift your hips until your body forms a straight line from shoulders to knees, hold for 3 seconds, and slowly lower back down.', 'body_part': 'Hip', 'is_free': False, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEiH_5zxH7e8nGfRs7k_EZUkoOJqsCgutIMsKD2LzydGi3QmGTJ_BkFHV6yfmpYnkaMozdoYWrsCkfvJBWbnzGrXhfxZrF5gbMv3RUO40chf6kV466IGwjWTNFqKuEUEyUAtpmCAm0Jev5OUWx1OPcJzTEjcTgll0Wqwc_F3mgPcYo3jl5vnh5Xhr41lkvMO'}, {'id': 'cc9ba5d6-4e0d-4e01-99ff-3bcf95952ec9', 'title': 'GLUTE SQUEEZE', 'description': 'Lie on your back or sit upright, squeeze your buttock muscles as tight as possible for 5 seconds, then relax and repeat.', 'body_part': 'Glutes', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEg7iekspghjCYWg7W9iD22-iz78xYTHJ7B5Z1cKS_f0e6P-hITOY5MioFGrIrtsusY2qvB0OUMBHbSNSA8mafoLashDN78S5PRF-rowf0_8RJM35On-mLh8uLLaKlGoR1p3y8ALWbzEoMkevc3IN87o3hyDK7OupJqBCy7s7-_sC50j8Nb7XXn2k-G3VnrH=w421-h421'}, {'id': '896577cb-5e24-4bbb-a202-6d718fca1e59', 'title': 'CHIN TUCKS', 'description': 'To perform this exercise, sit tall and look straight ahead while gently drawing your head straight back as if making a double chin, ensuring your eyes remain level and your head does not tilt downward.', 'body_part': 'Neck', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEg1otRS0f7rL8OY3jMVApU7UoI7jwXVDXEdGLcV-BN5knGupEY4jlryCtKGzLv-DVSZkIYl5KNQ-wBiWqsUa9I3bgnOffYMbwEDetW_oQmzuU7J5QeCxRkjuR1sajj7b4D_bdaNe4G0LKPBbF2l470U4nRYm3-ZNtVv7hitubbOgTXzEEdymUV5ABJQpzmE'}, {'id': '790a2b24-881e-46f4-82d8-aff281375127', 'title': 'Biceps curls', 'description': 'Instruction', 'body_part': 'Arms', 'is_free': True, 'video_url': None}, {'id': '88a1340f-34bb-446e-9cd6-85e69de1c99d', 'title': 'NECK SIDE STRETCH', 'description': 'Sit on one hand to keep your shoulder stabilized and use your other hand to gently pull your head toward the opposite shoulder until you feel a comfortable stretch along the side of the neck.', 'body_part': 'Neck', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEg-w49qaZjspvJDbaoPEvrPxhDjz0o8y8uLvqHj0zgoMh2nqTrsRiZjbMrOeFzUA4Wob5AEyRlZQr5cnM2VjwhsC0BJ-xOyJdL0W99KgTSgogcLGP_L2x1HhrHMtlrBNgWB86zMUIPuXdxLdq9Y-Bt4gOA7SGJnXBSRr4I62d_zsq7Ha5N8SKUijNajKjsV'}, {'id': '4f791ed7-02d3-4f8b-9c8e-0562ad2bc47b', 'title': 'PENDULUM EXERCISE', 'description': 'Lean forward and let your arm hang down loosely so that you can use your body weight to gently swing the arm in small circles or forward and backward motions for early mobilization.', 'body_part': 'Shoulder', 'is_free': False, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEiq9tuCzJGSWRHnOfjS-lnNZzEEthn4eerjB3Xe-Voysh_AvSTNixXqSRhdgS8BN1Rnk7OZp1Cp6K9SRYa3dm6Cv7yhuioeyyrRqSQZi1Czr7gMHqhLIsc5eMPMg6hGtHtfe0CgGlma680TeMVTcL9LVBeb5HeFYsVfKSKzbtmmInN42fTC39TMARTyLHMC'}, {'id': '5e1e726c-c8ae-459a-805f-6386f2617f18', 'title': 'WALL SLIDES', 'description': 'Stand with your back and arms against a wall in a goal post position and slowly slide your arms up the wall as high as you can without arching your back before sliding them back down.', 'body_part': 'Shoulder', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEjCtkYSRT0S3EeOS1c32wYwZGp6hdWETYcQuIzJyIC55dcsoYheJQlcJy1Bdq5mWqw810WYu1rqJt6E_RIT6QNHgusRnwFqLrv7YBc4O99kspAGftqIZ8cClcs2rM-gd_yxa4_mNayaTAlVbWgArGHyQwLW74zRsetR0a9SWOBgo2f5KXJof1M9lAoDroLs'}, {'id': 'e4f225f1-9f9b-4ad7-9d6d-5906d88accd9', 'title': 'SCAPULAR SQUEEZES', 'description': 'Sit or stand with a tall posture and squeeze your shoulder blades together as if you are trying to hold a pencil between them or place them into your back pockets.', 'body_part': 'Upper Back', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEik5U1sB1u1jNYzh87HqeFKLazwI3aF5qiv9F6AtC3VA0yWJc4HTInC-NeqEPB3oNOzQXE0TALVegMnlm9hShgKHppVYfV_Wsiz3mKybhr_sgoiuvKdRhEqYm2ZzwAv2lGFW8VA0IDyV5clxXVUGP6Xb552sb1421V5SUlWfpOJ42ZCzE16qCelKpFywKPw'}, {'id': '5fde4185-fca3-4b78-b855-817cc49d12d4', 'title': 'CAT COW STRETCH', 'description': 'On your hands and knees, alternate between arching your back up toward the ceiling while tucking your chin and letting your belly drop down while looking up to promote spinal mobility.', 'body_part': 'Spine', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEgD9E-9BXDTTp8dokF3eXE4aa4Wpca7WJK-tJNRnjMani5AWAHBVM5mEvqNSvlDFInaOge8AfLWZcyTXjDUxniNXK0LeZ3A5KIZa4oMH_J3_IrCfoZOWjavuZ5BCvWus3N24uZfD4SBhTQwSYHpCkIHxrQQuC3o5jqUt0gWb-9k35Ik3jr66aaK0OLWh7M-'}, {'id': '7c0c3aec-c862-4809-bbf1-2e78b8659776', 'title': 'CERVICAL FLEXION ISOMETRICS (Front Press)', 'description': 'Place your palm on your forehead. Gently try to push your head forward while resisting with your hand.', 'body_part': 'Neck', 'is_free': False, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEhNQFtzQSNzk6r4h2V7fbNJ8agucyZIQ59wCutgdxpexCfw7PckxsK_lTK9eJkL4rg_jmT8z8-Tg_aJijL0nMkt8sAuktr9YqtrtsS6zSDueMmLDRWaKnI5tKKy66-aY1KegAh323H99Xk-ZvwECz2DMXh4txuBbMLnAKtii_CKfZX4bOToJX94_1IV8veH'}, {'id': 'f92e64d0-09a1-4546-ad71-298101664106', 'title': 'CERVICAL  EXTENSION ISOMETRICS  (Back Press)', 'description': 'Place both hands behind your head. Try to push your head backward while resisting with your hands.', 'body_part': 'Neck', 'is_free': False, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEhBQ3EPL_PjSs7LUEeHbICEku44KF5P1W-zjCvQhwK6ewT0W1mMyO4MSrryFCoVOMk2wHGHF9nmRg86NWJNZ3pQktwtrYk-qrUzm2wUn5-NoQCLcnaSKS5rXbsivHciaz8YqCyB_ajfkGbAhA7u9d4se5jPeza8ajg5Xm0jC8JvS-I5c56lVN5Sh4Azlv2P'}, {'id': '1b16c80a-a684-4cec-8762-60ef44203647', 'title': 'LATERAL FLEXION  ISOMETRIC  – Right Side', 'description': 'Place your right hand on the right side of your head. Gently push your head towards the shoulder while resisting with your hand.', 'body_part': 'Other', 'is_free': True, 'video_url': 'https://blogger.googleusercontent.com/img/a/AVvXsEjmFV9AAA-vJwTjP6e13pu1XzIQ9iYiLuwispoIOjn8U19WTs5xyBsBTHvCjKyjAOsplSKGwP__jmtN1VI-L7Td5nRDxZNK45Xc_xxPuLaod9BKM43XNb1CMrx8tEupoIVPJoKMp_4sci5FHdgkZaKQ2HffCeXOCVtptWbP7rJiZoSyCv8LF95cDVRnqFKx'}]


def upgrade() -> None:
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
    now = datetime.utcnow()
    seed_data = [
        {
            "id": uuid.UUID(row["id"]),
            "clinic_id": None,
            "title": row["title"],
            "description": row["description"],
            "body_part": row["body_part"],
            "is_free": row["is_free"],
            "video_url": row["video_url"],
            "created_at": now,
            "updated_at": now,
        }
        for row in SEED_EXERCISES
    ]
    if seed_data:
        op.bulk_insert(exercises_table, seed_data)
        print(f"Seeded {len(seed_data)} global exercises (static, no network call).")


def downgrade() -> None:
    op.execute("DELETE FROM exercises WHERE clinic_id IS NULL")
