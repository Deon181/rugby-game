import pytest
from fastapi import HTTPException
from sqlmodel import select

from backend.app.models.entities import Player, PlayerMedicalAssignment, TeamTactics, WeeklyPerformancePlan
from backend.app.schemas.api import MedicalAssignmentUpdateRequest, PerformancePlanUpdateRequest, SelectionUpdateRequest
from backend.app.services.career import advance_offseason
from backend.app.services.game import get_selection, update_selection
from backend.app.services.performance import get_performance_overview, update_medical_assignment, update_performance_plan
from backend.app.services.progression import apply_between_week_recovery
from backend.tests.helpers import create_test_save, play_out_regular_season


def test_performance_endpoint_seeds_default_plan(client):
    client.post(
        "/api/saves",
        json={
            "template_team_id": 1,
            "club_name": "Granite Coast RFC",
            "club_short_name": "GCR",
            "name": "Performance Save",
        },
    )

    overview = client.get("/api/performance")
    tactics = client.get("/api/tactics")

    assert overview.status_code == 200
    assert tactics.status_code == 200
    payload = overview.json()
    assert payload["plan"]["focus"] == tactics.json()["training_focus"]
    assert payload["plan"]["intensity"] == "balanced"
    assert payload["plan"]["contact_level"] == "balanced"


def test_performance_plan_update_mirrors_tactics(session):
    save = create_test_save(session)
    team_tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == save.user_team_id)).first()
    original_focus = team_tactics.training_focus
    assert original_focus

    response = update_performance_plan(
        session,
        PerformancePlanUpdateRequest(focus="recovery", intensity="heavy", contact_level="high"),
    )

    refreshed_tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == save.user_team_id)).first()
    assert response.plan.focus == "recovery"
    assert response.plan.intensity == "heavy"
    assert response.plan.contact_level == "high"
    assert refreshed_tactics.training_focus == "recovery"


def test_between_week_recovery_creates_managed_return_assignment(session):
    save = create_test_save(session)
    overview = get_performance_overview(session)
    assert overview.plan.focus
    user_player = session.exec(select(Player).where(Player.team_id == save.user_team_id).order_by(Player.id)).first()
    user_player.injury_status = "Hamstring strain"
    user_player.injury_weeks_remaining = 1
    session.add(user_player)
    session.commit()

    # reset current-week preparation so the recovery pass runs in the test harness
    plan = session.exec(select(WeeklyPerformancePlan).where(WeeklyPerformancePlan.team_id == save.user_team_id)).first()
    plan.prepared = False
    session.add(plan)
    session.commit()

    mutated = apply_between_week_recovery(session, save)
    session.commit()

    assignment = session.exec(
        select(PlayerMedicalAssignment)
        .where(PlayerMedicalAssignment.team_id == save.user_team_id)
        .where(PlayerMedicalAssignment.player_id == user_player.id)
        .where(PlayerMedicalAssignment.week == 1)
    ).first()
    refreshed_player = session.get(Player, user_player.id)

    assert mutated is True
    assert refreshed_player.injury_weeks_remaining == 0
    assert refreshed_player.injury_status == "Healthy"
    assert assignment is not None
    assert assignment.clearance_status == "managed"
    assert assignment.return_watch_weeks == 1


def test_medical_out_assignment_blocks_selection(session):
    create_test_save(session)
    selection = get_selection(session)
    blocked_player_id = selection.starting_lineup[0].player_id

    update_medical_assignment(
        session,
        blocked_player_id,
        MedicalAssignmentUpdateRequest(clearance_status="out"),
    )

    with pytest.raises(HTTPException, match="unavailable"):
        update_selection(session, SelectionUpdateRequest(**selection.model_dump()))


def test_new_season_seeds_week_one_performance_plan(session):
    save = create_test_save(session)
    update_performance_plan(
        session,
        PerformancePlanUpdateRequest(focus="defense", intensity="light", contact_level="low"),
    )

    play_out_regular_season(session)
    advance_offseason(session)
    advance_offseason(session)
    advance_offseason(session)
    advance_offseason(session)

    plan = session.exec(
        select(WeeklyPerformancePlan)
        .where(WeeklyPerformancePlan.save_game_id == save.id)
        .where(WeeklyPerformancePlan.team_id == save.user_team_id)
        .where(WeeklyPerformancePlan.season_number == 2)
        .where(WeeklyPerformancePlan.week == 1)
    ).first()

    assert plan is not None
    assert plan.prepared is True
