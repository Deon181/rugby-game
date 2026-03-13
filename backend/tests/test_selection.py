from backend.app.schemas.api import SelectionSlotRead, SelectionUpdateRequest
from backend.app.services.selection import SelectionValidationError, validate_selection
from backend.tests.helpers import create_test_save, team_bundle


def test_lineup_validation_rejects_duplicate_players(session):
    save = create_test_save(session)
    _, players, _, _ = team_bundle(session, save.user_team_id)
    duplicated_player = players[0]
    request = SelectionUpdateRequest(
        starting_lineup=[SelectionSlotRead(slot=slot, player_id=duplicated_player.id) for slot in [
            "Loosehead Prop",
            "Hooker",
            "Tighthead Prop",
            "Lock",
            "Lock",
            "Blindside Flanker",
            "Openside Flanker",
            "Number 8",
            "Scrumhalf",
            "Flyhalf",
            "Wing",
            "Inside Centre",
            "Outside Centre",
            "Wing",
            "Fullback",
        ]],
        bench_player_ids=[player.id for player in players[1:9]],
        captain_id=duplicated_player.id,
        goal_kicker_id=duplicated_player.id,
    )

    try:
        validate_selection(players, request)
        raise AssertionError("Expected validation to fail for duplicate players.")
    except SelectionValidationError as exc:
        assert "23 unique players" in str(exc)
