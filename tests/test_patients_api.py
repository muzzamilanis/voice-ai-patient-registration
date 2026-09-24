from datetime import date, timedelta

REQUIRED = {
    "first_name": "Ava",
    "last_name": "Patel",
    "date_of_birth": "03/04/1991",
    "sex": "Female",
    "phone_number": "3125550101",
    "address_line_1": "500 Lake Shore Drive",
    "city": "Chicago",
    "state": "IL",
    "zip_code": "60611",
}


def test_create_list_get_update_soft_delete(client):
    created = client.post("/patients", json=REQUIRED)
    assert created.status_code == 201
    body = created.json()
    assert body["error"] is None
    patient_id = body["data"]["patient_id"]
    assert body["data"]["phone_number"] == "3125550101"

    listed = client.get("/patients?last_name=Patel")
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

    fetched = client.get(f"/patients/{patient_id}")
    assert fetched.json()["data"]["city"] == "Chicago"

    updated = client.put(f"/patients/{patient_id}", json={"city": "Evanston"})
    assert updated.status_code == 200
    assert updated.json()["data"]["city"] == "Evanston"

    deleted = client.delete(f"/patients/{patient_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None

    missing = client.get(f"/patients/{patient_id}")
    assert missing.status_code == 404

    listed_after = client.get("/patients")
    assert listed_after.json()["data"] == []


def test_rejects_future_dob(client):
    payload = dict(REQUIRED)
    payload["date_of_birth"] = (date.today() + timedelta(days=10)).strftime("%m/%d/%Y")
    res = client.post("/patients", json=payload)
    assert res.status_code == 422
    assert res.json()["data"] is None
    assert res.json()["error"] is not None


def test_rejects_short_phone(client):
    payload = dict(REQUIRED)
    payload["phone_number"] = "555"
    res = client.post("/patients", json=payload)
    assert res.status_code == 422


def test_filter_by_phone(client):
    client.post("/patients", json=REQUIRED)
    res = client.get("/patients?phone_number=(312) 555-0101")
    assert len(res.json()["data"]) == 1


def test_unknown_patient_404(client):
    res = client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    assert res.json()["error"]["message"] == "patient not found"
