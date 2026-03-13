from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    project_name: str = "Rugby Director API"
    api_prefix: str = "/api"
    db_path: Path = Path("backend/rugby_director.db")
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
