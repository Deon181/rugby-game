from sqlmodel import select

from sqlmodel import Session

from backend.app.db.session import engine, init_db
from backend.app.models.entities import SaveGame
from backend.app.seed.generator import create_save_world


def main() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(SaveGame).where(SaveGame.active.is_(True))).first():
            print("Active save already exists.")
            return
        save = create_save_world(session, chosen_template_team_id=1, save_name="Demo Save")
        print(f"Created demo save {save.id} for team {save.user_team_id}.")


if __name__ == "__main__":
    main()
