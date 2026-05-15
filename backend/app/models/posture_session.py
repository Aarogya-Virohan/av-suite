import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Float, Text
from typing import Optional
from app.models.base import Base, TimestampMixin

class PostureSession(Base, TimestampMixin):
    __tablename__ = "posture_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    
    clinic = relationship("Clinic", back_populates="posture_sessions")
    patient = relationship("Patient", back_populates="posture_sessions")
    measurements = relationship("PostureMeasurement", back_populates="session", cascade="all, delete-orphan")


class PostureMeasurement(Base, TimestampMixin):
    __tablename__ = "posture_measurements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_sessions.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session = relationship("PostureSession", back_populates="measurements")
