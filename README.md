# Voice AI Agent — Patient Registration

Working implementation of the take-home: REST API + persistent SQLite store + voice intake that writes through the same service layer.

The original `muzzamilanis/Voice-AI-Agent` repo could be read but not written (GitHub connector 403 on refs). This repo is the one with the code.

## Honest status

Works locally end-to-end:
- `POST /patients` and the rest of the required CRUD, including soft delete
- validation for names, DOB, sex, US phone, state, ZIP
- `POST /voice/simulate` collects fields, confirms, persists
- duplicate phone lookup
- dashboard at `/`
- `pytest` coverage for validators, API, and the text voice path

Does **not** include a live US number. There are no Vapi/Twilio credentials in this environment. That fails the "we will call the number" bar until you attach a Vapi number to a deployed copy. The FAQ in the brief allows documenting that blocker. `/voice/simulate` is the local substitute.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
pytest -q
```

API: `http://localhost:8000`  
Dashboard: `http://localhost:8000/`  
Health: `http://localhost:8000/health`

## Architecture

- `app/routers/patients.py` — REST envelope `{data, error}`
- `app/services/patient_service.py` — CRUD, soft delete, phone lookup
- `app/validators.py` + `app/schemas.py` — server-side rules; voice is not trusted
- `app/voice/prompt.py` — system prompt for Vapi
- `app/voice/agent.py` — deterministic intake used by `/voice/simulate`
- `app/routers/voice.py` — simulator + Vapi tool webhooks
- `app/models.py` — SQLite schema + `call_logs`

The agent never writes SQL. It calls the same service the API uses.

## Attach a real number

1. Deploy this API with a public HTTPS URL.
2. Create a Vapi assistant from `vapi/assistant.json`.
3. Paste `SYSTEM_PROMPT` from `app/voice/prompt.py`.
4. Point tool URLs at `/voice/tools/lookup_patient_by_phone`, `/create_patient`, `/update_patient`.
5. Put the number and public API URL at the top of this README.

## Known limits

- No provisioned phone number in this PR.
- Simulate sessions are in-memory; patients are not.
- SQLite is the 3-hour persistence choice, not a clinic database.
- HIPAA is out of scope per the brief. Do not store real patient data.
- Deterministic agent is weaker than GPT-4o on messy speech. That is the cost of a testable repo without a paid key.
