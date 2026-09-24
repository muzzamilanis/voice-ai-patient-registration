"""SQLAlchemy models. Schema is the source of truth for persistence constraints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Patient(Base):
    """Minimum U.S. healthcare demographic record plus soft-delete metadata."""

    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(10), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    address_line_1: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    insurance_provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance_member_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(40), nullable=True, default="English")
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_patients_last_name", "last_name"),
        Index("ix_patients_dob", "date_of_birth"),
        Index("ix_patients_phone", "phone_number"),
    )


class CallLog(Base):
    """Observability: final payload and optional transcript for each voice session."""

    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    caller_phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
