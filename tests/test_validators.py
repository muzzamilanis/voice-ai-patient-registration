from datetime import date, timedelta

import pytest

from app.validators import (
    ValidationError,
    normalize_phone,
    normalize_sex,
    normalize_state,
    normalize_zip,
    parse_date_of_birth,
)


def test_phone_strips_formatting():
    assert normalize_phone("(415) 555-0199") == "4155550199"
    assert normalize_phone("+1 415 555 0199") == "4155550199"


def test_phone_rejects_short_number():
    with pytest.raises(ValidationError) as exc:
        normalize_phone("415555")
    assert exc.value.field == "phone_number"


def test_future_dob_rejected():
    future = (date.today() + timedelta(days=3)).strftime("%m/%d/%Y")
    with pytest.raises(ValidationError):
        parse_date_of_birth(future)


def test_dob_parses_iso_and_us():
    assert parse_date_of_birth("04/12/1988") == date(1988, 4, 12)
    assert parse_date_of_birth("1988-04-12") == date(1988, 4, 12)


def test_state_accepts_full_name():
    assert normalize_state("California") == "CA"
    assert normalize_state("ca") == "CA"


def test_zip_plus_four():
    assert normalize_zip("94105-1234") == "94105-1234"
    assert normalize_zip("94105") == "94105"


def test_sex_aliases():
    assert normalize_sex("f") == "Female"
    assert normalize_sex("Decline") == "Decline to Answer"
