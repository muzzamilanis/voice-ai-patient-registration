"""Engine, session factory, and schema bootstrap."""

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    path = url.replace("sqlite:///", "", 1)
    if path in {":memory:", ""}:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, future=True)


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that always closes the session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_if_empty(db: Session) -> None:
    """Load two demo patients so the API is not empty on first boot."""
    from datetime import date

    from app.config import settings
    from app.models import Patient

    if settings.app_env == "test":
        return

    existing = db.execute(text("SELECT COUNT(*) FROM patients")).scalar_one()
    if existing:
        return
    samples = [
        Patient(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1988, 4, 12),
            sex="Female",
            phone_number="4155550199",
            email="jane.doe@example.com",
            address_line_1="123 Market Street",
            address_line_2="Apt 4B",
            city="San Francisco",
            state="CA",
            zip_code="94105",
            insurance_provider="Blue Shield of California",
            insurance_member_id="BSC1234567",
            preferred_language="English",
            emergency_contact_name="John Doe",
            emergency_contact_phone="4155550188",
        ),
        Patient(
            first_name="Marcus",
            last_name="Nguyen",
            date_of_birth=date(1975, 11, 3),
            sex="Male",
            phone_number="2065550142",
            email="marcus.nguyen@example.com",
            address_line_1="800 Pine Street",
            city="Seattle",
            state="WA",
            zip_code="98101",
            preferred_language="English",
        ),
    ]
    db.add_all(samples)
    db.commit()
