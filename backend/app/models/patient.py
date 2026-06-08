"""
Module: patient.py
Purpose: Patient entity database model definition
Yeh module Patient database model define karta hai jo patient information
ko store karta hai (name, DOB, contact, etc.) aur clinic/user relationships manage karta hai.

Key Components:
- Patient class: Patient entity ko represent karta hai
- Relationships: Clinic, User, Prescriptions, PostureSessions se connections

Database Table: patients
"""

import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, ForeignKey
from datetime import date
from typing import Optional
from app.models.base import Base, TimestampMixin


class Patient(Base, TimestampMixin):
    """
    Class ka purpose: Patient entity ko represent karna database mein
    Yeh class patient ka complete record store karta hai jismein
    personal information, clinic association, aur user linking hota hai.
    
    Database Table: patients
    
    Fields Description:
    - id: Unique identifier (UUID primary key) - Har patient ka unique ID
    - clinic_id: Clinic ko identify karta hai (Foreign Key) - Multi-tenant isolation
    - user_id: Linked user account (nullable) - Optional user account ke liye
    - first_name: Patient ka first name (String, required) - Admin display ke liye
    - last_name: Patient ka last name (String, required) - Admin display ke liye
    - date_of_birth: Patient ki DOB (Date, nullable) - Age calculation aur records ke liye
    - phone: Contact number (String, nullable) - Communication purpose
    - created_at: Record creation time (inherited from TimestampMixin) - Audit trail
    - updated_at: Last modification time (inherited from TimestampMixin) - Audit trail
    
    Relationships:
    - clinic: Clinic model se one-to-many relationship
            Multiple patients ek clinic mein ho sakte hain
            CASCADE DELETE: agar clinic delete ho to patient bhi delete hoga
    
    - user: User model se optional one-to-one relationship
           Ek patient ek user account se link ho sakta hai
           SET NULL: agar user delete ho to user_id null hoga
    
    - prescriptions: Prescription model se one-to-many relationship
                    Ek patient ke multiple prescriptions ho sakte hain
                    Yeh back_populates karta hai prescription mein
    
    - posture_sessions: PostureSession model se one-to-many relationship
                       Ek patient ke multiple posture sessions ho sakte hain
                       Yeh tracking karta hai patient ke posture data
    
    Usage Example:
    # Patient create karna
    new_patient = Patient(
        clinic_id=clinic_uuid,
        first_name="John",
        last_name="Doe",
        phone="9876543210"
    )
    session.add(new_patient)
    await session.commit()
    
    # Patient retrieve karna with relationships
    patient = await session.get(Patient, patient_id)
    print(patient.clinic.name)  # Clinic access
    print(patient.prescriptions)  # Prescriptions list
    """
    
    __tablename__ = "patients"

    # Primary Key - Unique identifier
    # UUID generate hota hai automatically har new record ke liye
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Clinic Association - Foreign Key relationship
    # Required field - Patient hamesha kisi clinic se associated hona chahiye
    # CASCADE DELETE: agar clinic delete ho to patient bhi delete hoga
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    
    # User Association - Optional Foreign Key relationship
    # Nullable: Patient ka user account ho sakta hai ya nahi bhi
    # SET NULL: agar user delete ho to user_id null set hota hai
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Personal Information - Required fields
    # first_name: Patient identification ke liye zaroori
    # Maximum 100 characters for practical names
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # last_name: Patient identification ke liye zaroori
    # Maximum 100 characters consistent with first_name
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Date of Birth - Optional field
    # Medical history aur age-related calculations ke liye useful
    # Nullable: Kabhi kabhi DOB available nahi hota
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Phone Contact - Optional field
    # Communication ke liye zaroori
    # Maximum 20 characters international format ke liye (+91-9876543210)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships - Database connections
    # Yeh relationships SQLAlchemy lazy loading aur relationships traversal enable karte hain
    
    # Clinic relationship - Back reference se clinic.patients access kar sakte hain
    clinic = relationship("Clinic", back_populates="patients")
    
    # User relationship - Ek patient ke user account se link
    user = relationship("User", back_populates="patient_profile")
    
    # Prescriptions relationship - Patient ke sare prescriptions
    prescriptions = relationship("Prescription", back_populates="patient")
    
    # Posture Sessions relationship - Patient ke sare posture measurements/sessions
    posture_sessions = relationship("PostureSession", back_populates="patient")
