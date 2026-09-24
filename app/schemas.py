"""Pydantic request/response contracts for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.validators import (
    normalize_email,
    normalize_member_id,
    normalize_name,
    normalize_optional_text,
    normalize_phone,
    normalize_sex,
    normalize_state,
    normalize_zip,
    parse_date_of_birth,
)


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date | str
    sex: str
    phone_number: str
    email: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name")
    @classmethod
    def _first(cls, v: str) -> str:
        return normalize_name(v, "first_name")

    @field_validator("last_name")
    @classmethod
    def _last(cls, v: str) -> str:
        return normalize_name(v, "last_name")

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: date | str) -> date:
        return parse_date_of_birth(v)

    @field_validator("sex")
    @classmethod
    def _sex(cls, v: str) -> str:
        return normalize_sex(v)

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v, "phone_number")

    @field_validator("email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        return normalize_email(v)

    @field_validator("address_line_1")
    @classmethod
    def _addr1(cls, v: str) -> str:
        cleaned = normalize_optional_text(v, "address_line_1", 200)
        if not cleaned:
            raise ValueError("address_line_1 is required")
        return cleaned

    @field_validator("address_line_2")
    @classmethod
    def _addr2(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "address_line_2", 200)

    @field_validator("city")
    @classmethod
    def _city(cls, v: str) -> str:
        cleaned = normalize_optional_text(v, "city", 100)
        if not cleaned:
            raise ValueError("city is required")
        return cleaned

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        return normalize_state(v)

    @field_validator("zip_code")
    @classmethod
    def _zip(cls, v: str) -> str:
        return normalize_zip(v)

    @field_validator("insurance_provider")
    @classmethod
    def _ins(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "insurance_provider", 120)

    @field_validator("insurance_member_id")
    @classmethod
    def _member(cls, v: Optional[str]) -> Optional[str]:
        return normalize_member_id(v)

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v: Optional[str]) -> Optional[str]:
        cleaned = normalize_optional_text(v, "preferred_language", 40)
        return cleaned or "English"

    @field_validator("emergency_contact_name")
    @classmethod
    def _ec_name(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "emergency_contact_name", 100)

    @field_validator("emergency_contact_phone")
    @classmethod
    def _ec_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or str(v).strip() == "":
            return None
        return normalize_phone(v, "emergency_contact_phone")


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    """All fields optional so PUT can apply a partial update."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date | str] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "PatientUpdate":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("at least one field is required for an update")
        return self

    @field_validator("first_name")
    @classmethod
    def _first(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_name(v, "first_name")

    @field_validator("last_name")
    @classmethod
    def _last(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_name(v, "last_name")

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: Optional[date | str]) -> Optional[date]:
        return None if v is None else parse_date_of_birth(v)

    @field_validator("sex")
    @classmethod
    def _sex(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_sex(v)

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_phone(v, "phone_number")

    @field_validator("email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        return normalize_email(v)

    @field_validator("address_line_1")
    @classmethod
    def _addr1(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_optional_text(v, "address_line_1", 200)

    @field_validator("address_line_2")
    @classmethod
    def _addr2(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "address_line_2", 200)

    @field_validator("city")
    @classmethod
    def _city(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_optional_text(v, "city", 100)

    @field_validator("state")
    @classmethod
    def _state(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_state(v)

    @field_validator("zip_code")
    @classmethod
    def _zip(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else normalize_zip(v)

    @field_validator("insurance_provider")
    @classmethod
    def _ins(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "insurance_provider", 120)

    @field_validator("insurance_member_id")
    @classmethod
    def _member(cls, v: Optional[str]) -> Optional[str]:
        return normalize_member_id(v)

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "preferred_language", 40)

    @field_validator("emergency_contact_name")
    @classmethod
    def _ec_name(cls, v: Optional[str]) -> Optional[str]:
        return normalize_optional_text(v, "emergency_contact_name", 100)

    @field_validator("emergency_contact_phone")
    @classmethod
    def _ec_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or str(v).strip() == "":
            return None
        return normalize_phone(v, "emergency_contact_phone")


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    email: Optional[str]
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str]
    insurance_member_id: Optional[str]
    preferred_language: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class Envelope(BaseModel):
    data: Any = None
    error: Any = None


class VoiceToolLookup(BaseModel):
    phone_number: str = Field(..., description="Caller or stated 10-digit U.S. phone number")


class VoiceSimulateTurn(BaseModel):
    session_id: Optional[str] = None
    message: str
    caller_phone: Optional[str] = None
