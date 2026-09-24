"""Field-level validation used by both the REST API and the voice agent.

The voice layer is not trusted. Every value is re-checked here before a write.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

SEX_VALUES = ("Male", "Female", "Other", "Decline to Answer")

# Hyphen is last in the class so it cannot form a range.
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '.-]{0,49}$")
ZIP_PATTERN = re.compile(r"^[0-9]{5}(-[0-9]{4})?$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MEMBER_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


class ValidationError(ValueError):
    """Raised when a single field fails a rule. Carries the field name."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def normalize_name(value: str, field: str) -> str:
    cleaned = " ".join((value or "").strip().split())
    if not cleaned or len(cleaned) > 50 or not NAME_PATTERN.match(cleaned):
        raise ValidationError(
            field,
            f"{field} must be 1-50 letters and may include spaces, hyphens, or apostrophes",
        )
    return cleaned


def parse_date_of_birth(value: str | date) -> date:
    """Accept MM/DD/YYYY, YYYY-MM-DD, or a date object. Reject future dates."""
    if isinstance(value, date) and not isinstance(value, datetime):
        dob = value
    else:
        raw = str(value).strip()
        dob = None
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                dob = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        if dob is None:
            raise ValidationError("date_of_birth", "Date of birth must be a valid date in MM/DD/YYYY")
    if dob > date.today():
        raise ValidationError("date_of_birth", "Date of birth cannot be in the future")
    if dob.year < 1900:
        raise ValidationError("date_of_birth", "Date of birth year must be 1900 or later")
    return dob


def normalize_sex(value: str) -> str:
    raw = (value or "").strip()
    lookup = {item.lower(): item for item in SEX_VALUES}
    aliases = {
        "m": "Male",
        "f": "Female",
        "male": "Male",
        "female": "Female",
        "other": "Other",
        "prefer not to say": "Decline to Answer",
        "decline": "Decline to Answer",
        "decline to answer": "Decline to Answer",
        "nonbinary": "Other",
        "non-binary": "Other",
    }
    key = raw.lower()
    resolved = lookup.get(key) or aliases.get(key)
    if not resolved:
        raise ValidationError("sex", "Sex must be Male, Female, Other, or Decline to Answer")
    return resolved


def _digits_only(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def normalize_phone(value: str, field: str = "phone_number") -> str:
    """Strip formatting and require exactly 10 US digits (optionally prefixed with 1)."""
    digits = _digits_only(value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValidationError(field, f"{field} must be a valid 10-digit U.S. phone number")
    if digits[0] == "0":
        raise ValidationError(field, f"{field} is not a valid U.S. phone number")
    return digits


def format_phone_display(digits: str) -> str:
    d = _digits_only(digits)
    if len(d) != 10:
        return digits
    return f"({d[0:3]}) {d[3:6]}-{d[6:10]}"


def normalize_email(value: Optional[str]) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    cleaned = str(value).strip().lower()
    if not EMAIL_PATTERN.match(cleaned) or len(cleaned) > 254:
        raise ValidationError("email", "email must be a valid email address")
    return cleaned


def normalize_state(value: str) -> str:
    code = (value or "").strip().upper()
    full_names = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
        "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
        "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
        "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
        "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
        "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE",
        "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
        "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC",
        "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
        "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
        "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
        "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
        "DISTRICT OF COLUMBIA": "DC", "WASHINGTON DC": "DC",
    }
    if code in full_names:
        code = full_names[code]
    if code not in US_STATES:
        raise ValidationError("state", "state must be a valid 2-letter U.S. state abbreviation")
    return code


def normalize_zip(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) == 5:
        formatted = digits
    elif len(digits) == 9:
        formatted = f"{digits[:5]}-{digits[5:]}"
    else:
        raise ValidationError("zip_code", "zip_code must be 5-digit or ZIP+4 U.S. format")
    if not ZIP_PATTERN.match(formatted):
        raise ValidationError("zip_code", "zip_code must be 5-digit or ZIP+4 U.S. format")
    return formatted


def normalize_optional_text(value: Optional[str], field: str, max_len: int = 100) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    if cleaned == "":
        return None
    if len(cleaned) > max_len:
        raise ValidationError(field, f"{field} must be at most {max_len} characters")
    return cleaned


def normalize_member_id(value: Optional[str]) -> Optional[str]:
    cleaned = normalize_optional_text(value, "insurance_member_id", 64)
    if cleaned is None:
        return None
    if not MEMBER_ID_PATTERN.match(cleaned):
        raise ValidationError("insurance_member_id", "insurance_member_id must be alphanumeric")
    return cleaned
