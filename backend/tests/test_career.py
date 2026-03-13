from sqlmodel import select

from backend.app.models.entities import Fixture, SaveGame, TeamSeasonSummary, YouthProspect
from backend.app.services.career import advance_offseason, promote_youth_prospect
from backend.tests.helpers import create_test_save, play_out_regular_season


def test_season_review_and_rollover_create_new_season_state(session):
    save = create_test_save(session)
    play_out_regular_season(session)

    refreshed_save = session.exec(select(SaveGame).where(SaveGame.id == save.id)).first()
    summaries = session.exec(
        select(TeamSeasonSummary).where(TeamSeasonSummary.save_game_id == save.id).where(TeamSeasonSummary.season_number == 1)
    ).all()

    assert refreshed_save.phase == "season_review"
    assert refreshed_save.offseason_step == "review"
    assert len(summaries) == 10

    advance_offseason(session)
    advance_offseason(session)
    prospects = session.exec(
        select(YouthProspect).where(YouthProspect.save_game_id == save.id).where(YouthProspect.team_id == save.user_team_id)
    ).all()
    assert prospects

    promote_youth_prospect(session, prospects[0].id)
    advance_offseason(session)
    save_after_rollover = advance_offseason(session)

    new_save = session.exec(select(SaveGame).where(SaveGame.id == save.id)).first()
    season_two_fixtures = session.exec(
        select(Fixture).where(Fixture.save_game_id == save.id).where(Fixture.season_number == 2)
    ).all()

    assert save_after_rollover.phase == "in_season"
    assert new_save.season_number == 2
    assert new_save.current_week == 1
    assert len(season_two_fixtures) == 90
