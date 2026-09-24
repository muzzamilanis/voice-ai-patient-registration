"""Voice integration endpoints: simulator, Vapi tool webhooks, end-of-call log."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.http import failure, success
from app.schemas import PatientCreate, PatientUpdate, VoiceSimulateTurn
from app.services import patient_service as svc
from app.validators import ValidationError
from app.voice.agent import GREETING, get_or_create_session, handle_turn
from app.voice.prompt import SYSTEM_PROMPT

logger = logging.getLogger("voice_agent")
router = APIRouter(prefix="/voice", tags=["voice"])


def _check_secret(header_value: Optional[str]) -> Optional[Any]:
    if not settings.vapi_webhook_secret:
        return None
    if header_value != settings.vapi_webhook_secret:
        return failure("unauthorized webhook", status_code=401)
    return None


@router.get("/prompt")
def get_prompt():
    """Expose the system prompt so reviewers do not have to hunt through files."""
    return success({"system_prompt": SYSTEM_PROMPT, "greeting": GREETING})


@router.post("/simulate")
def simulate_turn(body: VoiceSimulateTurn, db: Session = Depends(get_db)):
    """Text stand-in for a live call. Same collection, confirm, and persist path."""
    session = get_or_create_session(body.session_id, body.caller_phone)
    if not session.transcript:
        session.transcript.append(f"agent: {GREETING}")
        if not body.message.strip():
            return success({"session_id": session.session_id, "reply": GREETING, "phase": session.phase, "collected": {}, "saved": False})
    result = handle_turn(db, session, body.message)
    logger.info("voice.simulate %s", json.dumps(result.get("collected"), default=str))
    return success(result)


@router.post("/tools/{tool_name}")
def vapi_tool(
    tool_name: str,
    request_body: dict[str, Any],
    db: Session = Depends(get_db),
    x_vapi_secret: Optional[str] = Header(default=None),
):
    """Vapi custom-tool target. Arguments may be nested under message.toolCallList or sent flat."""
    denied = _check_secret(x_vapi_secret)
    if denied:
        return denied

    args = _extract_tool_args(request_body)
    logger.info("voice.tool %s args=%s", tool_name, json.dumps(args, default=str))

    try:
        if tool_name == "lookup_patient_by_phone":
            phone = args.get("phone_number") or args.get("phone")
            if not phone:
                return success({"found": False, "reason": "phone_number is required"})
            found = svc.find_active_by_phone(db, phone)
            return success({"found": bool(found), "patient": found})

        if tool_name == "create_patient":
            created = svc.create_patient(db, PatientCreate(**args))
            logger.info("voice.create_patient %s", json.dumps(created, default=str))
            svc.log_call(
                db,
                outcome="created",
                payload_json=json.dumps(created, default=str),
                patient_id=created["patient_id"],
                caller_phone=created.get("phone_number"),
            )
            return success({"ok": True, "patient": created})

        if tool_name == "update_patient":
            patient_id = args.pop("patient_id", None)
            if not patient_id:
                return failure("patient_id is required", status_code=422)
            updated = svc.update_patient(db, patient_id, PatientUpdate(**args))
            logger.info("voice.update_patient %s", json.dumps(updated, default=str))
            svc.log_call(
                db,
                outcome="updated",
                payload_json=json.dumps(updated, default=str),
                patient_id=updated["patient_id"],
                caller_phone=updated.get("phone_number"),
            )
            return success({"ok": True, "patient": updated})

        return failure(f"unknown tool {tool_name}", status_code=404)
    except svc.NotFoundError:
        return failure("patient not found", status_code=404)
    except ValidationError as exc:
        return failure(exc.message, status_code=422, details={"field": exc.field})
    except Exception as exc:  # noqa: BLE001
        logger.exception("voice.tool failed")
        return failure("tool failed", status_code=500, details=str(exc))


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_vapi_secret: Optional[str] = Header(default=None),
):
    """Catch-all Vapi server URL. Logs end-of-call reports; routes tool calls."""
    denied = _check_secret(x_vapi_secret)
    if denied:
        return denied
    payload = await request.json()
    message = payload.get("message") or payload
    msg_type = message.get("type") if isinstance(message, dict) else None
    logger.info("voice.webhook type=%s", msg_type)

    if msg_type == "end-of-call-report":
        artifact = message.get("artifact") or {}
        transcript = artifact.get("transcript") or message.get("transcript")
        analysis = message.get("analysis") or {}
        svc.log_call(
            db,
            outcome="call_ended",
            payload_json=json.dumps(analysis, default=str)[:8000],
            transcript=transcript,
            caller_phone=(message.get("customer") or {}).get("number"),
        )
        return success({"ok": True})

    return success({"ok": True, "ignored": msg_type})


def _extract_tool_args(body: dict[str, Any]) -> dict[str, Any]:
    if not body:
        return {}
    if "message" in body and isinstance(body["message"], dict):
        calls = body["message"].get("toolCallList") or body["message"].get("toolCalls") or []
        if calls:
            fn = calls[0].get("function") or {}
            args = fn.get("arguments") or calls[0].get("arguments") or {}
            if isinstance(args, str):
                return json.loads(args or "{}")
            return args
    if "phone_number" in body or "first_name" in body or "patient_id" in body:
        return body
    return body.get("arguments") or body
