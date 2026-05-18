"""
Module: exercise.py
Purpose: Exercise entity database model definition
Yeh module Exercise database model define karta hai jo rehabilitation exercises
ko store karta hai (name, description, body part, video) aur clinic relationships manage karta hai.

Key Components:
- Exercise class: Exercise entity ko represent karta hai
- Relationships: Clinic aur PrescriptionItem se connections

Database Table: exercises
Usage: Exercises ko store karte hain jo doctors prescribe karte hain patients ko
"""

import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Text
from typing import Optional
from app.models.base import Base, TimestampMixin


class Exercise(Base, TimestampMixin):
    """
    Class ka purpose: Exercise entity ko represent karna database mein
    Yeh class rehabilitation exercise ko define karta hai jismein
    exercise details, body part target, aur multimedia content (video) hota hai.
    
    Database Table: exercises
    
    Fields Description:
    - id: Unique identifier (UUID primary key) - Har exercise ka unique ID
    - clinic_id: Clinic ko identify karta hai (Foreign Key, nullable) - Multi-clinic support
    - title: Exercise name (String, required) - Display aur identification ke liye
    - description: Detailed explanation (Text, nullable) - Admin aur patient education ke liye
    - body_part: Target body part (String, nullable) - Categorization aur filtering ke liye
    - is_free: Free/Paid flag (Boolean, default False) - Subscription/pricing logic ke liye
    - video_url: Exercise video URL (String, nullable) - Patient instruction video link
    - created_at: Record creation time (inherited from TimestampMixin) - Audit trail
    - updated_at: Last modification time (inherited from TimestampMixin) - Audit trail
    
    Relationships:
    - clinic: Clinic model se optional many-to-one relationship
             Multiple exercises ek clinic ke ho sakte hain
             Nullable: Global exercises bhi ho sakte hain (clinic_id = NULL)
             CASCADE DELETE: agar clinic delete ho to exercise bhi delete hoga
    
    - prescription_items: PrescriptionItem model se one-to-many relationship
                         Ek exercise multiple prescription items mein use ho sakta hai
                         Yeh prescription mein included exercises track karta hai
    
    Usage Example:
    # Exercise create karna
    new_exercise = Exercise(
        clinic_id=clinic_uuid,
        title="Shoulder Rotation",
        description="Rotate shoulder in circular motion",
        body_part="Shoulder",
        is_free=True,
        video_url="https://cdn.example.com/exercise-001.mp4"
    )
    session.add(new_exercise)
    await session.commit()
    
    # Free exercises retrieve karna
    free_exercises = await session.execute(
        select(Exercise).where(Exercise.is_free == True)
    )
    
    # Exercise aur usne prescriptions retrieve karna
    exercise = await session.get(Exercise, exercise_id)
    print(exercise.prescription_items)  # Jis prescriptions mein use hua
    """
    
    __tablename__ = "exercises"

    # Primary Key - Unique identifier
    # UUID generate hota hai automatically har new record ke liye
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Clinic Association - Optional Foreign Key relationship
    # Nullable: Exercise either clinic-specific ho ya global ho sakta hai
    # CASCADE DELETE: agar clinic delete ho to exercise bhi delete hoga
    # Design: Flexibility provide karta hai shared exercises ke liye
    clinic_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Exercise Title - Required field
    # Display name jo admin aur doctors use karte hain
    # Maximum 255 characters practical exercise name ke liye
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Exercise Description - Optional detailed explanation
    # Text field unlimited size ke liye detailed instructions
    # Admin aur patients ko step-by-step guide dene ke liye
    # Nullable: Koi kabhi sirf title se exercise define kar sakta hai
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Body Part Target - Optional categorization
    # Anatomical body part jo exercise target karta hai
    # Examples: "Shoulder", "Knee", "Spine", "Hip"
    # Maximum 100 characters standard anatomical terms ke liye
    # Nullable: Kabhi generalized exercises ho sakte hain
    # Usage: Filtering, categorization, aur recommendations ke liye
    body_part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Free/Paid Flag - Pricing aur subscription logic
    # Boolean: True = Free (all patients), False = Paid/Restricted
    # Default: False (conservative, paid by default)
    # Usage: Subscription system aur access control mein
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Video URL - Multimedia instruction
    # URL link to exercise instruction video
    # Maximum 1024 characters long URLs accommodate karne ke liye
    # Nullable: Text-based exercises bhi ho sakte hain
    # Format: Typically CDN URL (AWS S3, Azure Blob, etc.)
    # Usage: Patient education aur demonstration ke liye
    video_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Relationships - Database connections
    # Yeh relationships SQLAlchemy lazy loading aur traversal enable karte hain
    
    # Clinic relationship - Back reference se clinic.exercises access kar sakte hain
    # Ek exercise ka ek clinic ho sakta hai (ya koi bhi nahi - global exercise)
    clinic = relationship("Clinic", back_populates="exercises")
    
    # Prescription Items relationship - Exercise ke sare prescription usages
    # Ek exercise multiple prescription items mein use ho sakta hai
    # Reverse relationship: prescription_item.exercise se back access
    prescription_items = relationship("PrescriptionItem", back_populates="exercise")
