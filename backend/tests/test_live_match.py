from backend.app.schemas.api import LiveMatchHalftimeRequest
from backend.app.services.live_match import get_current_live_match, start_live_match, submit_halftime_changes, tick_live_match
from backend.tests.helpers import create_test_save


def test_live_match_reaches_halftime_and_accepts_changes(session):
    create_test_save(session)

    snapshot = start_live_match(session)
    assert snapshot.status == "first_half"

    while snapshot.status != "halftime":
        snapshot = tick_live_match(session)

    starter = next(player for player in snapshot.user_matchday_players if player.on_field)
    replacement = next(
        player
        for player in snapshot.user_matchday_players
        if not player.on_field and (player.primary_position == starter.starter_slot or starter.starter_slot in player.secondary_positions)
    )
    updated_tactics = snapshot.user_tactics.model_dump()
    updated_tactics["attacking_style"] = "expansive"

    resumed = submit_halftime_changes(
        session,
        LiveMatchHalftimeRequest(
            tactics=updated_tactics,
            substitutions=[{"player_out_id": starter.player_id, "player_in_id": replacement.player_id}],
            captain_id=snapshot.user_selection.captain_id,
            goal_kicker_id=snapshot.user_selection.goal_kicker_id,
        ),
    )

    assert resumed.status == "second_half"
    assert resumed.user_tactics.attacking_style == "expansive"
    assert any(player.player_id == replacement.player_id and player.on_field for player in resumed.user_matchday_players)
    assert get_current_live_match(session) is not None
