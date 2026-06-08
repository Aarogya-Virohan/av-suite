import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def seed_exercises():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        exercises = [
            ("Neck Isometric Flexion", "Neck", "Cervical Spondylosis", "Hold your hand against your forehead and push forward.", True),
            ("Shoulder External Rotation", "Shoulder", "Rotator Cuff Tendinopathy", "Keep elbow at side, rotate arm outward.", True),
            ("Lumbar Extension in Prone", "Back", "Disc Bulge", "Lie on stomach and push chest up with arms.", True),
            ("Knee Extension (Short Arc)", "Knee", "Osteoarthritis", "Place towel under knee, straighten the knee.", True),
            ("Ankle Dorsiflexion with Band", "Ankle", "Ankle Sprain", "Pull foot up against resistance band.", True),
            ("Wall Slides", "Shoulder", "Shoulder Impingement", "Slide hands up the wall while facing it.", False),
            ("Bridges", "Back", "Non-specific low back pain", "Lie on back, bend knees, lift hips.", True),
        ]
        
        for name, part, condition, desc, free in exercises:
            # Check if exists
            res = await conn.execute(text("SELECT id FROM exercises WHERE title = :title"), {"title": name})
            if not res.fetchone():
                await conn.execute(
                    text("""
                        INSERT INTO exercises (id, title, description, body_part, is_free)
                        VALUES (:id, :title, :desc, :part, :free)
                    """),
                    {"id": str(uuid.uuid4()), "title": name, "desc": desc, "part": part, "free": free}
                )
        print("Exercises seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_exercises())
