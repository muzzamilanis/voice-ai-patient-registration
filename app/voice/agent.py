"""Deterministic intake agent used when no LLM key is configured.

Accepts free-text answers, extracts what it can, re-prompts only missing or
invalid fields, supports corrections and start-over, looks up duplicates by
phone, confirms before write, and talks through API failures.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.schemas import PatientCreate, PatientUpdate
from app.services import patient_service as svc
from app.validators import (
    ValidationError,
    format_phone_display,
    normalize_email,
    normalize_name,
    normalize_optional_text,
    normalize_phone,
    normalize_sex,
    normalize_state,
    normalize_zip,
    parse_date_of_birth,
)
from app.voice.prompt import GREETING

REQUIRED_ORDER = [
    "first_name", "last_name", "date_of_birth", "sex", "phone_number",
    "address_line_1", "city", "state", "zip_code",
]
OPTIONAL_FIELDS = [
    "email", "address_line_2", "insurance_provider", "insurance_member_id",
    "preferred_language", "emergency_contact_name", "emergency_contact_phone",
]
FIELD_PROMPTS = {
    "first_name": "What's your first name?",
    "last_name": "And your last name?",
    "date_of_birth": "What's your date of birth? Month, day, and year.",
    "sex": "And how should we record your sex — male, female, other, or decline to answer?",
    "phone_number": "What's the best 10-digit U.S. phone number to reach you?",
    "address_line_1": "What's your street address?",
    "city": "What city is that in?",
    "state": "Which state?",
    "zip_code": "And the ZIP code?",
}
SESSIONS: dict[str, "IntakeSession"] = {}


@dataclass
class IntakeSession:
    session_id: str
    caller_phone: Optional[str] = None
    fields: dict[str, Any] = field(default_factory=dict)
    phase: str = "collect"
    existing: Optional[dict] = None
    update_mode: bool = False
    transcript: list[str] = field(default_factory=list)
    language: str = "en"


def get_or_create_session(session_id: Optional[str], caller_phone: Optional[str]) -> IntakeSession:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    sid = session_id or str(uuid.uuid4())
    session = IntakeSession(session_id=sid, caller_phone=caller_phone)
    SESSIONS[sid] = session
    return session


def _yes(text: str) -> bool:
    return bool(re.search(r"\\b(yes|yeah|yep|correct|right|sounds good|that's right|that is right|confirm|ok|okay|sure)\\b", text, re.I))


def _no(text: str) -> bool:
    return bool(re.search(r"\\b(no|nope|nah|wrong|incorrect|not quite|start over|start again)\\b", text, re.I))


def _wants_start_over(text: str) -> bool:
    return bool(re.search(r"\\b(start over|start again|reset|from the beginning)\\b", text, re.I))


def _wants_spanish(text: str) -> bool:
    return bool(re.search(r"hablo espa[nñ]ol|en espa[nñ]ol|speak spanish", text, re.I))


def _next_missing(session: IntakeSession) -> Optional[str]:
    for key in REQUIRED_ORDER:
        if key not in session.fields or session.fields[key] in (None, ""):
            return key
    return None


def handle_turn(db: Session, session: IntakeSession, user_text: str) -> dict:
    text = (user_text or "").strip()
    session.transcript.append(f"user: {text}")
    if _wants_spanish(text):
        session.language = "es"
        return _say(session, "Claro. Podemos continuar en español. ¿Cuál es su nombre y apellido?")
    if _wants_start_over(text):
        session.fields, session.phase, session.existing, session.update_mode = {}, "collect", None, False
        return _say(session, "No problem. We'll start fresh. What's your first and last name?")
    if session.phase == "done":
        return _say(session, "You're already registered. If you need to change something, say start over.")
    if session.phase == "confirm":
        return _handle_confirm(db, session, text)
    if session.phase == "optional_offer":
        return _handle_optional(session, text)
    _extract_into(session, text)
    if "phone_number" in session.fields and session.existing is None:
        try:
            session.existing = svc.find_active_by_phone(db, session.fields["phone_number"])
        except ValidationError:
            session.existing = None
        if session.existing and not session.update_mode:
            session.phase = "duplicate"
            return _say(session, f"It looks like we already have a record for {session.existing['first_name']} {session.existing['last_name']}. Would you like to update your information instead?")
    if session.phase == "duplicate":
        if _yes(text):
            session.update_mode, session.phase = True, "collect"
            for key in REQUIRED_ORDER + OPTIONAL_FIELDS:
                if key not in session.fields and session.existing.get(key) not in (None, ""):
                    session.fields[key] = session.existing[key]
            return _say(session, "Okay, we'll update that record. What would you like to change?")
        if _no(text):
            session.existing, session.phase = None, "collect"
        else:
            return _say(session, "Should I update the existing record, or keep going with a new one?")
    missing = _next_missing(session)
    if missing:
        reply = FIELD_PROMPTS[missing]
        if missing == "date_of_birth" and re.search(r"\\d", text):
            reply = "I need a real date of birth that isn't in the future, like March 4th 1988."
        if missing == "phone_number" and re.search(r"\\d", text):
            reply = "That number doesn't look like a 10-digit U.S. phone number. Can you say it again with the area code?"
        return _say(session, reply)
    session.phase = "optional_offer"
    return _say(session, "I have the required details. I can also collect insurance, an emergency contact, and preferred language. Would you like to add any of those?")


def _handle_optional(session: IntakeSession, text: str) -> dict:
    if not _no(text):
        _extract_into(session, text)
    session.phase = "confirm"
    return _say(session, f"Let me read this back. {_summary(session)}. Does that all sound correct?")


def _handle_confirm(db: Session, session: IntakeSession, text: str) -> dict:
    if _wants_start_over(text) or _no(text):
        session.phase = "collect"
        return _say(session, "Which field should I correct?")
    if not _yes(text):
        return _say(session, "Please say yes if that's correct, or tell me which field to change.")
    try:
        if session.update_mode and session.existing:
            patient = svc.update_patient(
                db, session.existing["patient_id"],
                PatientUpdate(**{k: v for k, v in session.fields.items() if v is not None}),
            )
            outcome = "updated"
        else:
            patient = svc.create_patient(db, PatientCreate(**session.fields))
            outcome = "created"
    except Exception as exc:  # noqa: BLE001
        svc.log_call(db, outcome="write_failed", payload_json=json.dumps(session.fields, default=str),
                     transcript="\\n".join(session.transcript),
                     caller_phone=session.fields.get("phone_number") or session.caller_phone)
        return _say(session, "I wasn't able to save that just now. A coordinator will follow up. I'm sorry for the trouble.", error=str(exc))
    session.phase = "done"
    svc.log_call(db, outcome=outcome, payload_json=json.dumps(patient, default=str),
                 transcript="\\n".join(session.transcript), patient_id=patient["patient_id"],
                 caller_phone=patient.get("phone_number") or session.caller_phone)
    return _say(session, f"You're all set, {patient['first_name']}. You're registered. Thank you for calling Northstar.", patient=patient, saved=True)


def _summary(session: IntakeSession) -> str:
    f = session.fields
    dob = f.get("date_of_birth")
    dob_s = dob.strftime("%m/%d/%Y") if hasattr(dob, "strftime") else str(dob)
    phone = format_phone_display(str(f.get("phone_number", "")))
    return f"{f.get('first_name')} {f.get('last_name')}; born {dob_s}; sex {f.get('sex')}; phone {phone}; address {f.get('address_line_1')} {f.get('city')}, {f.get('state')} {f.get('zip_code')}"


def _extract_into(session: IntakeSession, text: str) -> None:
    raw = text.strip()
    tokens = [t for t in re.split(r"\\s+", raw) if t]
    if 2 <= len(tokens) <= 4 and all(re.match(r"^[A-Za-z][A-Za-z\\-']*$", t) for t in tokens):
        if not re.search(r"\\b(yes|no|male|female|street|avenue|apt)\\b", raw, re.I):
            try:
                session.fields.setdefault("first_name", normalize_name(tokens[0], "first_name"))
                session.fields.setdefault("last_name", normalize_name(tokens[-1], "last_name"))
            except ValidationError:
                pass
    dob = re.search(r"\\b(\\d{1,2}[/-]\\d{1,2}[/-]\\d{4})\\b", raw)
    if dob:
        try:
            session.fields["date_of_birth"] = parse_date_of_birth(dob.group(1))
        except ValidationError:
            pass
    spoken = re.search(r"\\b(january|february|march|april|may|june|july|august|september|october|november|december)\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(\\d{4})\\b", raw, re.I)
    if spoken:
        months = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        try:
            stamp = f"{months[spoken.group(1).lower()]:02d}/{int(spoken.group(2)):02d}/{spoken.group(3)}"
            session.fields["date_of_birth"] = parse_date_of_birth(stamp)
        except ValidationError:
            pass
    try:
        session.fields["sex"] = normalize_sex(raw)
    except ValidationError:
        pass
    phone = re.search(r"(\\+?1[\\s.-]?)?\\(?\\d{3}\\)?[\\s.-]?\\d{3}[\\s.-]?\\d{4}", raw)
    if phone:
        try:
            session.fields["phone_number"] = normalize_phone(phone.group(0))
        except ValidationError:
            pass
    try:
        session.fields["state"] = normalize_state(raw)
    except ValidationError:
        pass
    zip_match = re.search(r"\\b(\\d{5}(?:-\\d{4})?)\\b", raw)
    if zip_match:
        try:
            session.fields["zip_code"] = normalize_zip(zip_match.group(1))
        except ValidationError:
            pass
    if _next_missing(session) == "address_line_1" and re.search(r"\\d+\\s+\\w+", raw):
        addr = normalize_optional_text(raw, "address_line_1", 200)
        if addr:
            session.fields["address_line_1"] = addr
    if _next_missing(session) == "city" and re.match(r"^[A-Za-z][A-Za-z\\s\\-']+$", raw):
        city = normalize_optional_text(raw, "city", 100)
        if city:
            session.fields["city"] = city


def _say(session: IntakeSession, reply: str, **extra: Any) -> dict:
    session.transcript.append(f"agent: {reply}")
    return {
        "session_id": session.session_id,
        "reply": reply,
        "phase": session.phase,
        "collected": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in session.fields.items()},
        "saved": extra.get("saved", False),
        "patient": extra.get("patient"),
        "error": extra.get("error"),
    }
