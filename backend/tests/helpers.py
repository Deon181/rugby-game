from __future__ import annotations

from sqlmodel import Session, select

from backend.app.models.entities import Player, Team, TeamSelection, TeamTactics
from backend.app.schemas.api import LiveMatchHalftimeRequest
from backend.app.seed.generator import create_save_world
from backend.app.services.live_match import start_live_match, submit_halftime_changes, tick_live_match
from backend.app.simulation.engine import TeamProfile, build_team_profile


def create_test_save(session: Session, club_id: int = 1):
    return create_save_world(
        session,
        chosen_template_team_id=club_id,
        save_name="Test Save",
        club_name=f"Test Club {club_id}",
        club_short_name=f"TC{club_id}",
    )


def team_bundle(session: Session, team_id: int) -> tuple[Team, list[Player], TeamSelection, TeamTactics]:
    team = session.get(Team, team_id)
    players = session.exec(select(Player).where(Player.team_id == team_id)).all()
    selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team_id)).first()
    tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == team_id)).first()
    return team, players, selection, tactics


def team_profile(session: Session, team_id: int) -> TeamProfile:
    team, players, selection, tactics = team_bundle(session, team_id)
    return build_team_profile(team, players, selection, tactics)


def play_live_week(session: Session):
    snapshot = start_live_match(session)
    while snapshot.status != "full_time":
        if snapshot.status == "halftime":
            snapshot = submit_halftime_changes(
                session,
                LiveMatchHalftimeRequest(
                    tactics=snapshot.user_tactics.model_dump(),
                    substitutions=[],
                    captain_id=snapshot.user_selection.captain_id,
                    goal_kicker_id=snapshot.user_selection.goal_kicker_id,
                ),
            )
        else:
            snapshot = tick_live_match(session)
    return snapshot


def play_out_regular_season(session: Session) -> None:
    for _ in range(18):
        play_live_week(session)
