from sqlalchemy import or_
from sqlmodel import select

from backend.app.models.entities import BoardState, FinanceTransaction, Fixture, SaveGame
from backend.app.schemas.api import FinanceSettingsUpdateRequest
from backend.app.services.career import advance_offseason
from backend.app.services.finance import get_finance_overview, update_finance_settings
from backend.app.services.recruitment import get_recruitment_board
from backend.app.services.transfers import make_transfer_bid, renew_contract
from backend.tests.helpers import create_test_save, play_live_week, play_out_regular_season


def test_finance_endpoint_initializes_board_state(client):
    client.post(
        "/api/saves",
        json={
            "template_team_id": 1,
            "club_name": "Summit Bridge RFC",
            "club_short_name": "SBR",
            "name": "Finance Save",
        },
    )

    response = client.get("/api/finance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["board"]["operating_focus"] == "balanced"
    assert payload["board"]["confidence"] > 0
    assert payload["summary"]["transfer_budget"] > 0


def test_weekly_finance_transactions_created_once(session):
    save = create_test_save(session)

    get_finance_overview(session)
    play_live_week(session)

    transactions = session.exec(
        select(FinanceTransaction)
        .where(FinanceTransaction.save_game_id == save.id)
        .where(FinanceTransaction.team_id == save.user_team_id)
        .where(FinanceTransaction.season_number == save.season_number)
        .where(FinanceTransaction.week == 1)
    ).all()
    categories = [transaction.category for transaction in transactions]

    assert categories.count("sponsor_income") == 1
    assert categories.count("weekly_wages") == 1
    assert categories.count("operating_cost") == 1


def test_home_gate_income_only_applies_on_home_weeks(session):
    save = create_test_save(session)
    saw_home_week = False
    saw_away_week = False

    for _ in range(6):
        current_save = session.exec(select(SaveGame).where(SaveGame.id == save.id)).first()
        user_fixture = session.exec(
            select(Fixture)
            .where(Fixture.save_game_id == save.id)
            .where(Fixture.season_number == current_save.season_number)
            .where(Fixture.week == current_save.current_week)
            .where(or_(Fixture.home_team_id == save.user_team_id, Fixture.away_team_id == save.user_team_id))
        ).first()
        week = current_save.current_week
        is_home = user_fixture.home_team_id == save.user_team_id

        play_live_week(session)

        gate_transactions = session.exec(
            select(FinanceTransaction)
            .where(FinanceTransaction.save_game_id == save.id)
            .where(FinanceTransaction.team_id == save.user_team_id)
            .where(FinanceTransaction.season_number == current_save.season_number)
            .where(FinanceTransaction.week == week)
            .where(FinanceTransaction.category == "gate_receipts")
        ).all()

        if is_home:
            saw_home_week = True
            assert len(gate_transactions) == 1
        else:
            saw_away_week = True
            assert not gate_transactions

        if saw_home_week and saw_away_week:
            break

    assert saw_home_week
    assert saw_away_week


def test_operating_focus_changes_cost_profile(session):
    create_test_save(session)

    balanced = get_finance_overview(session)
    performance = update_finance_settings(session, FinanceSettingsUpdateRequest(operating_focus="performance"))
    commercial = update_finance_settings(session, FinanceSettingsUpdateRequest(operating_focus="commercial"))

    assert performance.board.operating_focus == "performance"
    assert commercial.board.operating_focus == "commercial"
    assert performance.summary.weekly_operating_cost > balanced.summary.weekly_operating_cost
    assert commercial.summary.weekly_operating_cost < balanced.summary.weekly_operating_cost


def test_transfer_and_contract_events_hit_finance_ledger(session):
    save = create_test_save(session)
    board = get_recruitment_board(session)
    contract_player = board.contract_watch[0]

    renew_contract(session, contract_player.player_id, contract_player.desired_years, contract_player.desired_weekly_wage)
    refreshed_board = get_recruitment_board(session)
    listing = refreshed_board.market[0]
    make_transfer_bid(session, listing.listing_id, listing.asking_price)

    transactions = session.exec(
        select(FinanceTransaction)
        .where(FinanceTransaction.save_game_id == save.id)
        .where(FinanceTransaction.team_id == save.user_team_id)
        .order_by(FinanceTransaction.id)
    ).all()
    categories = [transaction.category for transaction in transactions]

    assert "contract_commitment" in categories
    assert "transfer_fee" in categories


def test_offseason_rollover_carries_board_focus(session):
    save = create_test_save(session)
    update_finance_settings(session, FinanceSettingsUpdateRequest(operating_focus="commercial"))

    play_out_regular_season(session)
    advance_offseason(session)
    advance_offseason(session)
    advance_offseason(session)
    advance_offseason(session)

    next_season_board = session.exec(
        select(BoardState)
        .where(BoardState.save_game_id == save.id)
        .where(BoardState.team_id == save.user_team_id)
        .where(BoardState.season_number == 2)
    ).first()

    assert next_season_board is not None
    assert next_season_board.operating_focus == "commercial"
    assert next_season_board.confidence > 0
