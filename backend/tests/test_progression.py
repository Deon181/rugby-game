from sqlmodel import select

from backend.app.models.entities import Fixture, InboxMessage, MatchResult, SaveGame
from backend.tests.helpers import create_test_save, play_live_week


def test_advance_week_updates_world_state(session):
    save = create_test_save(session)

    response = play_live_week(session)

    refreshed_save = session.exec(select(SaveGame).where(SaveGame.id == save.id)).first()
    played_fixtures = session.exec(select(Fixture).where(Fixture.save_game_id == save.id).where(Fixture.played.is_(True))).all()
    results = session.exec(select(MatchResult).where(MatchResult.save_game_id == save.id)).all()
    inbox = session.exec(select(InboxMessage).where(InboxMessage.team_id == save.user_team_id)).all()

    assert refreshed_save.current_week == 2
    assert response.save.phase == "in_season"
    assert response.result is not None
    assert len(played_fixtures) == 5
    assert len(results) == 5
    assert any(message.type == "match" for message in inbox)
