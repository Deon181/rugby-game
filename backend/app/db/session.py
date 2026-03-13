from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.config import settings


engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
