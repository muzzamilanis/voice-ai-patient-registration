from app.voice.agent import SESSIONS, get_or_create_session


def test_full_registration_over_text(client):
    SESSIONS.clear()
    turns = [
        "Ava Patel",
        "March 4 1991",
        "Female",
        "312-555-0101",
        "500 Lake Shore Drive",
        "Chicago",
        "Illinois",
        "60611",
        "No",
        "Yes that's correct",
    ]
    session_id = None
    last = None
    for message in turns:
        payload = {"message": message, "session_id": session_id}
        res = client.post("/voice/simulate", json=payload)
        assert res.status_code == 200
        last = res.json()["data"]
        session_id = last["session_id"]
    assert last["saved"] is True
    assert last["patient"]["first_name"] == "Ava"
    listed = client.get("/patients?last_name=Patel")
    assert len(listed.json()["data"]) == 1


def test_invalid_phone_is_reprompted(client):
    SESSIONS.clear()
    session = get_or_create_session(None, None)
    session.fields.update(
        {
            "first_name": "Ava",
            "last_name": "Patel",
            "date_of_birth": __import__("datetime").date(1991, 3, 4),
            "sex": "Female",
        }
    )
    res = client.post(
        "/voice/simulate",
        json={"session_id": session.session_id, "message": "my number is 555"},
    )
    reply = res.json()["data"]["reply"].lower()
    assert "10-digit" in reply or "phone" in reply
    assert res.json()["data"]["saved"] is False


def test_start_over_clears_state(client):
    SESSIONS.clear()
    first = client.post("/voice/simulate", json={"message": "Ava Patel"})
    sid = first.json()["data"]["session_id"]
    reset = client.post("/voice/simulate", json={"session_id": sid, "message": "start over"})
    assert reset.json()["data"]["collected"] == {}
