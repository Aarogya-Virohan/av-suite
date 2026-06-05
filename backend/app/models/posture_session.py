"""
Module: posture_session.py
Purpose: Posture assessment database models definition
Yeh module PostureSession aur PostureMeasurement models define karta hai
jo patient ke posture data ko track karte hain (measurements, metrics, progress).

Key Components:
- PostureSession class: Patient ke posture assessment session ko represent karta hai
- PostureMeasurement class: Individual measurement/metric for session
- Relationships: Clinic, Patient, aur inter-model connections

Database Tables:
- posture_sessions: Patient posture assessment sessions store karte hain
- posture_measurements: Individual measurements within sessions store karte hain
"""

import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Float, Text
from typing import Optional
from app.models.base import Base, TimestampMixin


class PostureSession(Base, TimestampMixin):
    """
    Class ka purpose: Patient posture assessment session ko represent karna
    Yeh class patient ke posture data collection session define karta hai.
    Ek session mein multiple measurements (body angles, distances, etc.) ho sakte hain.
    
    Database Table: posture_sessions
    
    Fields Description:
    - id: Unique identifier (UUID primary key) - Har session ka unique ID
    - clinic_id: Clinic ko identify karta hai (Foreign Key) - Multi-tenant isolation
    - patient_id: Patient ko identify karta hai (Foreign Key) - Patient association
    - measurements: Multiple PostureMeasurement records - Session ke sare measurements
    - created_at: Session creation time (inherited from TimestampMixin) - Assessment timestamp
    - updated_at: Last modification time (inherited from TimestampMixin) - Update tracking
    
    Relationships:
    - clinic: Clinic model se many-to-one relationship
             Multiple sessions ek clinic mein ho sakte hain
             CASCADE DELETE: agar clinic delete ho to session bhi delete hoga
    
    - patient: Patient model se many-to-one relationship
              Multiple sessions ek patient ke ho sakte hain
              CASCADE DELETE: agar patient delete ho to session bhi delete hoga
    
    - measurements: PostureMeasurement model se one-to-many relationship
                   Ek session ke multiple measurements ho sakte hain
                   Cascade="all, delete-orphan": measurements automatically delete
    
    Design Pattern:
    - Session-based grouping: Har assessment session ek record
    - Time series data: Multiple sessions same patient ke track progress
    - Cascade deletion: Session delete ho to measurements bhi delete
    
    Usage Example:
    # New posture assessment session create karna
    new_session = PostureSession(
        clinic_id=clinic_uuid,
        patient_id=patient_uuid
    )
    session.add(new_session)
    await session.commit()
    
    # Session retrieve with measurements
    posture_session = await session.get(PostureSession, session_id)
    for measurement in posture_session.measurements:
        print(f"{measurement.metric_name}: {measurement.value} {measurement.unit}")
    
    # Patient ke sare sessions retrieve karna
    sessions = await session.execute(
        select(PostureSession).where(PostureSession.patient_id == patient_id)
    )
    """
    
    __tablename__ = "posture_sessions"

    # Primary Key - Unique identifier
    # UUID generate hota hai automatically har new session ke liye
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Clinic Association - Required Foreign Key relationship
    # Multi-tenant isolation: Session always ek specific clinic se associated
    # CASCADE DELETE: agar clinic delete ho to session bhi delete hoga
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE")
    )
    
    # Patient Association - Required Foreign Key relationship
    # Patient identification: Session always ek specific patient ke liye
    # CASCADE DELETE: agar patient delete ho to session bhi delete hoga
    # Time series: Same patient ke multiple sessions hote hain progress track karne ke liye
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE")
    )
    
    # Posture Analysis Data
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    annotated_front_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    annotated_back_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    annotated_left_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    annotated_right_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships - Database connections
    # Yeh relationships SQLAlchemy lazy loading aur traversal enable karte hain
    
    # Clinic relationship - Back reference se clinic.posture_sessions access kar sakte hain
    clinic = relationship("Clinic", back_populates="posture_sessions")
    
    # Patient relationship - Back reference se patient.posture_sessions access kar sakte hain
    patient = relationship("Patient", back_populates="posture_sessions")
    
    # Measurements relationship - Session ke sare posture measurements
    # Cascade configuration: "all, delete-orphan" taaki session delete mein measurements bhi delete ho
    # Foreign key orphans ko automatically clean up karte hain
    measurements = relationship(
        "PostureMeasurement",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class PostureMeasurement(Base, TimestampMixin):
    """
    Class ka purpose: Individual posture measurement/metric ko represent karna
    Yeh class ek single measurement define karta hai (e.g., "Cervical Angle: 45 degrees")
    Multiple measurements ek session mein combined hote hain complete posture assessment ke liye.
    
    Database Table: posture_measurements
    
    Fields Description:
    - id: Unique identifier (UUID primary key) - Har measurement ka unique ID
    - session_id: PostureSession ko identify karta hai (Foreign Key) - Session association
    - metric_name: Measurement ka naam (String, required) - "Cervical Angle", "Shoulder Height", etc.
    - value: Measurement ka numerical value (Float, required) - 45.5, 10.2, etc.
    - unit: Measurement unit (String, nullable) - "degrees", "cm", "inches", "%"
    - notes: Additional context/notes (Text, nullable) - Doctor observations, findings
    - created_at: Measurement creation time (inherited from TimestampMixin) - Data point timestamp
    - updated_at: Last modification time (inherited from TimestampMixin) - Update tracking
    
    Relationships:
    - session: PostureSession model se many-to-one relationship
              Multiple measurements ek session mein
              CASCADE DELETE: agar session delete ho to measurement delete hoga
    
    Data Model:
    - Metric-based: Har measurement ek specific metric ke value ko store karta hai
    - Flexible schema: Different metrics different sessions mein ho sakte hain
    - Unit support: Different measurement units support karte hain flexibility ke liye
    
    Usage Example:
    # Session mein measurements add karna
    measurement = PostureMeasurement(
        session_id=session_uuid,
        metric_name="Cervical Angle",
        value=45.5,
        unit="degrees",
        notes="Good posture, slight forward head position"
    )
    session.add(measurement)
    await session.commit()
    
    # Session ke sare measurements iterate karna
    measurements = await session.execute(
        select(PostureMeasurement).where(
            PostureMeasurement.session_id == session_id
        )
    )
    for m in measurements.scalars():
        print(f"{m.metric_name}: {m.value} {m.unit}")
    """
    
    __tablename__ = "posture_measurements"

    # Primary Key - Unique identifier
    # UUID generate hota hai automatically har new measurement ke liye
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Session Association - Required Foreign Key relationship
    # Parent session identification: Har measurement ek session se associated
    # CASCADE DELETE: agar session delete ho to measurement delete hoga
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posture_sessions.id", ondelete="CASCADE")
    )
    
    # Metric Name - Required field
    # Measurement ka type/name (e.g., "Cervical Angle", "Shoulder Height", "Spinal Deviation")
    # Maximum 100 characters standard medical measurement names ke liye
    # String name taaki flexible metrics define kar sakein
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Measurement Value - Required numerical field
    # Actual measurement value (45.5, 10.2, 98.7, etc.)
    # Float type decimals support karta hai precision ke liye
    # Examples: angles, distances, percentages, etc.
    value: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Measurement Unit - Optional field
    # Unit of measurement (degrees, cm, inches, %, kg, etc.)
    # Maximum 50 characters standard units ke liye
    # Nullable: Unit kabhi included na ho sakta hai
    # Usage: Display aur calculation mein unit clarity ke liye
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Severity and Visibility
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    visibility: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Notes/Observations - Optional detailed field
    # Doctor observations, findings, or additional context
    # Text field unlimited size ke liye detailed notes
    # Examples: "Good posture", "Forward head position detected", "Improvement from last session"
    # Nullable: Kabhi notes available na ho
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships - Database connections
    # Yeh relationships SQLAlchemy lazy loading aur traversal enable karte hain
    
    # Session relationship - Back reference se session.measurements access kar sakte hain
    # Parent session reference taaki session data access kar sakein
    session = relationship("PostureSession", back_populates="measurements")
