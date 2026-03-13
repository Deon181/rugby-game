from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from backend.app.core.config import settings
from backend.app.db.session import engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    engine.dispose()
    Path(settings.db_path).unlink(missing_ok=True)
    SQLModel.metadata.create_all(engine)
    yield
    engine.dispose()
    Path(settings.db_path).unlink(missing_ok=True)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
