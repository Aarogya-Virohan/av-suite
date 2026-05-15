import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from app.models.base import Base, TimestampMixin

class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users = relationship("User", back_populates="clinic")
    patients = relationship("Patient", back_populates="clinic")
    exercises = relationship("Exercise", back_populates="clinic")
    prescriptions = relationship("Prescription", back_populates="clinic")
    posture_sessions = relationship("PostureSession", back_populates="clinic")
