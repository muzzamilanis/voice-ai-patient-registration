"""Patient persistence and query logic. Routers stay thin."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CallLog, Patient, utcnow
from app.schemas import PatientCreate, PatientOut, PatientUpdate
from app.validators import parse_date_of_birth, normalize_phone, ValidationError


class NotFoundError(Exception):
    pass


def _to_out(row: Patient) -> dict:
    return PatientOut.model_validate(row).model_dump(mode="json")


def list_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    phone_number: Optional[str] = None,
    include_deleted: bool = False,
) -> list[dict]:
    stmt = select(Patient)
    if not include_deleted:
        stmt = stmt.where(Patient.deleted_at.is_(None))
    if last_name:
        stmt = stmt.where(Patient.last_name.ilike(last_name.strip()))
    if date_of_birth:
        dob = parse_date_of_birth(date_of_birth)
        stmt = stmt.where(Patient.date_of_birth == dob)
    if phone_number:
        digits = normalize_phone(phone_number, "phone_number")
        stmt = stmt.where(Patient.phone_number == digits)
    stmt = stmt.order_by(Patient.created_at.desc())
    rows = db.execute(stmt).scalars().all()
    return [_to_out(row) for row in rows]


def get_patient(db: Session, patient_id: str, include_deleted: bool = False) -> dict:
    row = db.get(Patient, patient_id)
    if row is None or (row.deleted_at is not None and not include_deleted):
        raise NotFoundError("patient not found")
    return _to_out(row)


def find_active_by_phone(db: Session, phone_number: str) -> Optional[dict]:
    digits = normalize_phone(phone_number, "phone_number")
    stmt = (
        select(Patient)
        .where(Patient.phone_number == digits, Patient.deleted_at.is_(None))
        .order_by(Patient.updated_at.desc())
    )
    row = db.execute(stmt).scalars().first()
    return _to_out(row) if row else None


def create_patient(db: Session, payload: PatientCreate) -> dict:
    row = Patient(**payload.model_dump())
    if not row.preferred_language:
        row.preferred_language = "English"
    row.created_at = utcnow()
    row.updated_at = row.created_at
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


def update_patient(db: Session, patient_id: str, payload: PatientUpdate) -> dict:
    row = db.get(Patient, patient_id)
    if row is None or row.deleted_at is not None:
        raise NotFoundError("patient not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


def soft_delete_patient(db: Session, patient_id: str) -> dict:
    row = db.get(Patient, patient_id)
    if row is None or row.deleted_at is not None:
        raise NotFoundError("patient not found")
    row.deleted_at = utcnow()
    row.updated_at = row.deleted_at
    db.commit()
    db.refresh(row)
    return _to_out(row)


def log_call(
    db: Session,
    *,
    outcome: str,
    payload_json: Optional[str] = None,
    transcript: Optional[str] = None,
    patient_id: Optional[str] = None,
    caller_phone: Optional[str] = None,
) -> None:
    db.add(
        CallLog(
            outcome=outcome,
            payload_json=payload_json,
            transcript=transcript,
            patient_id=patient_id,
            caller_phone=caller_phone,
        )
    )
    db.commit()
