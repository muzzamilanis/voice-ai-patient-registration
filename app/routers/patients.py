"""Patient REST endpoints. Server-side validation is mandatory."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.http import failure, success
from app.schemas import PatientCreate, PatientUpdate
from app.services import patient_service as svc
from app.validators import ValidationError

router = APIRouter(prefix="/patients", tags=["patients"])


def _validation_failure(exc: Exception):
    if isinstance(exc, ValidationError):
        return failure(exc.message, status_code=422, details={"field": exc.field})
    if isinstance(exc, PydanticValidationError):
        details = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []) if part != "body")
            details.append({"field": loc or "body", "message": err.get("msg")})
        return failure("validation failed", status_code=422, details=details)
    if isinstance(exc, ValueError):
        return failure(str(exc), status_code=422)
    raise exc


@router.get("")
def list_patients(
    last_name: Optional[str] = Query(default=None),
    date_of_birth: Optional[str] = Query(default=None),
    phone_number: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        rows = svc.list_patients(
            db,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
        )
        return success(rows)
    except (ValidationError, PydanticValidationError, ValueError) as exc:
        return _validation_failure(exc)


@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    try:
        return success(svc.get_patient(db, patient_id))
    except svc.NotFoundError:
        return failure("patient not found", status_code=404)


@router.post("")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    created = svc.create_patient(db, payload)
    return success(created, status_code=201)


@router.put("/{patient_id}")
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    try:
        return success(svc.update_patient(db, patient_id, payload))
    except svc.NotFoundError:
        return failure("patient not found", status_code=404)


@router.delete("/{patient_id}")
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    try:
        return success(svc.soft_delete_patient(db, patient_id))
    except svc.NotFoundError:
        return failure("patient not found", status_code=404)
