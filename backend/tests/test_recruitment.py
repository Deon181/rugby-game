import pytest
from fastapi import HTTPException
from sqlmodel import select

from backend.app.models.entities import RecruitmentTarget
from backend.app.services.recruitment import get_recruitment_board, start_scouting_target, toggle_shortlist_target
from backend.app.services.transfers import make_transfer_bid, renew_contract
from backend.tests.helpers import create_test_save, play_live_week


def test_recruitment_endpoints_track_shortlist_and_reports(client):
    client.post("/api/saves", json={"team_id": 1, "name": "Recruitment Save"})

    initial = client.get("/api/recruitment")
    assert initial.status_code == 200
    payload = initial.json()
    assert payload["market"]
    player_id = payload["market"][0]["player_id"]

    scouting = client.post(f"/api/recruitment/scouting/{player_id}")
    assert scouting.status_code == 200

    shortlist = client.post(f"/api/recruitment/shortlist/{player_id}")
    assert shortlist.status_code == 200

    refreshed = client.get("/api/recruitment")
    assert refreshed.status_code == 200
    listing = next(item for item in refreshed.json()["market"] if item["player_id"] == player_id)
    assert listing["shortlisted"] is True
    assert listing["scouting"]["stage"] == "unscouted"


def test_scouting_progresses_with_completed_weeks(session):
    create_test_save(session)
    board = get_recruitment_board(session)
    target_player_id = board.market[0].player_id

    start_scouting_target(session, target_player_id)
    toggle_shortlist_target(session, target_player_id)

    play_live_week(session)
    board_after_one_week = get_recruitment_board(session)
    first_report = next(listing for listing in board_after_one_week.market if listing.player_id == target_player_id)
    assert first_report.shortlisted is True
    assert first_report.scouting.stage == "regional"
    assert first_report.scouting.fit_label is not None

    play_live_week(session)
    play_live_week(session)
    board_after_three_weeks = get_recruitment_board(session)
    final_report = next(listing for listing in board_after_three_weeks.market if listing.player_id == target_player_id)
    assert final_report.scouting.stage == "complete"
    assert final_report.scouting.potential_low == final_report.scouting.potential_high


def test_contract_watch_demands_drive_renewal_thresholds(session):
    create_test_save(session)
    contract_watch = get_recruitment_board(session).contract_watch
    assert contract_watch
    player = contract_watch[0]

    with pytest.raises(HTTPException, match="below expectations"):
        renew_contract(session, player.player_id, player.desired_years, player.desired_weekly_wage - 500)

    accepted = renew_contract(session, player.player_id, player.desired_years, player.desired_weekly_wage)
    assert accepted["status"] == "accepted"


def test_completed_transfer_closes_recruitment_target(session):
    save = create_test_save(session)
    board = get_recruitment_board(session)
    listing = board.market[0]

    start_scouting_target(session, listing.player_id)
    toggle_shortlist_target(session, listing.player_id)
    result = make_transfer_bid(session, listing.listing_id, listing.asking_price)
    assert result["status"] == "accepted"

    target = session.exec(
        select(RecruitmentTarget)
        .where(RecruitmentTarget.save_game_id == save.id)
        .where(RecruitmentTarget.season_number == save.season_number)
        .where(RecruitmentTarget.player_id == listing.player_id)
    ).first()
    assert target is not None
    assert target.status == "signed"

    refreshed_board = get_recruitment_board(session)
    assert all(candidate.player_id != listing.player_id for candidate in refreshed_board.market)
