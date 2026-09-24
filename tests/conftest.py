import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + str(Path("/tmp/voice-ai-test.db"))
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient
import pytest

from app.database import SessionLocal, engine, init_db
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
