from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.models.entities import BoardState, FinanceTransaction, Fixture, InboxMessage, MatchResult, Player, SaveGame, Team
from backend.app.schemas.api import (
    BoardStatusRead,
    FinanceOverviewResponse,
    FinanceSettingsUpdateRequest,
    FinanceSummaryRead,
    FinanceTransactionRead,
    FinanceWeekBreakdownRead,
)
from backend.app.services.game import build_save_summary, build_table, get_active_save, get_user_team


OPERATING_FOCUS_VALUES = {"balanced", "performance", "commercial"}
RECURRING_WEEKLY_CATEGORIES = {"sponsor_income", "weekly_wages", "operating_cost", "gate_receipts"}


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _round_finance(value: float) -> int:
    return int(round(value / 1_000.0) * 1_000)


def pressure_state_for(confidence: int) -> str:
    if confidence >= 60:
        return "stable"
    if confidence >= 40:
        return "watch"
    return "critical"


def _objective_target_position(objective: str, team_count: int) -> int:
    objective_map = {
        "Win the title": 1,
        "Finish in the top three": min(3, team_count),
        "Reach the top half": max(1, team_count // 2),
        "Stabilise in the top half": max(1, team_count // 2),
        "Avoid the bottom three": max(1, team_count - 2),
        "Avoid finishing last": max(1, team_count - 1),
    }
    return objective_map.get(objective, max(1, team_count // 2))


def _current_wages(session: Session, team_id: int) -> int:
    return sum(player.wage for player in session.exec(select(Player).where(Player.team_id == team_id)).all())


def _focus_modifier(board_state: BoardState, *, balanced: int = 0, performance: int = 0, commercial: int = 0) -> int:
    if board_state.operating_focus == "performance":
        return performance
    if board_state.operating_focus == "commercial":
        return commercial
    return balanced


def weekly_sponsor_income(team: Team, board_state: BoardState) -> int:
    base = 175_000 + team.reputation * 3_250
    modifier = _focus_modifier(board_state, performance=-12_000, commercial=28_000)
    pressure = -18_000 if board_state.pressure_state == "critical" else -8_000 if board_state.pressure_state == "watch" else 0
    return _round_finance(base + modifier + pressure)


def weekly_operating_cost(team: Team, board_state: BoardState) -> int:
    staff_total = team.staff_attack + team.staff_defense + team.staff_fitness + team.staff_set_piece
    base = 88_000 + staff_total * 650
    modifier = _focus_modifier(board_state, performance=34_000, commercial=-16_000)
    return _round_finance(base + modifier)


def estimated_home_gate(team: Team, board_state: BoardState, result: MatchResult | None = None) -> int:
    form_bump = 0
    if result:
        if result.home_score > result.away_score:
            form_bump = 32_000
        elif result.home_score == result.away_score:
            form_bump = 14_000
        else:
            form_bump = -10_000
    focus_bump = _focus_modifier(board_state, performance=-6_000, commercial=22_000)
    return _round_finance(215_000 + team.reputation * 2_900 + form_bump + focus_bump)


def ensure_board_state(session: Session, save: SaveGame, team: Team) -> BoardState:
    board_state = session.exec(
        select(BoardState)
        .where(BoardState.save_game_id == save.id)
        .where(BoardState.team_id == team.id)
        .where(BoardState.season_number == save.season_number)
        .order_by(BoardState.id.desc())
    ).first()
    if board_state:
        return board_state

    previous = session.exec(
        select(BoardState)
        .where(BoardState.save_game_id == save.id)
        .where(BoardState.team_id == team.id)
        .where(BoardState.season_number == save.season_number - 1)
        .order_by(BoardState.id.desc())
    ).first()
    confidence = previous.confidence if previous else 64
    if previous:
        confidence = _clamp(round(previous.confidence * 0.7 + 20), 42, 84)
    board_state = BoardState(
        save_game_id=save.id,
        team_id=team.id,
        season_number=save.season_number,
        confidence=confidence,
        pressure_state=pressure_state_for(confidence),
        operating_focus=previous.operating_focus if previous else "balanced",
    )
    session.add(board_state)
    session.flush()
    return board_state


def _finance_transaction_read(transaction: FinanceTransaction) -> FinanceTransactionRead:
    return FinanceTransactionRead(
        id=transaction.id,
        week=transaction.week,
        category=transaction.category,
        amount=transaction.amount,
        balance_after=transaction.balance_after,
        note=transaction.note,
        created_at=transaction.created_at,
    )


def log_budget_transaction(
    session: Session,
    save: SaveGame,
    team: Team,
    *,
    category: str,
    amount: int,
    note: str,
    week: int | None = None,
) -> FinanceTransaction:
    applied_amount = amount
    if amount < 0:
        applied_amount = max(amount, -team.budget)
    team.budget += applied_amount
    transaction = FinanceTransaction(
        save_game_id=save.id,
        team_id=team.id,
        season_number=save.season_number,
        week=week or save.current_week,
        category=category,
        amount=applied_amount,
        balance_after=team.budget,
        note=note,
        created_at=datetime.now(timezone.utc),
    )
    session.add(team)
    session.add(transaction)
    session.flush()
    return transaction


def log_contract_commitment(
    session: Session,
    save: SaveGame,
    team: Team,
    *,
    player_name: str,
    previous_wage: int,
    new_wage: int,
    years: int,
) -> FinanceTransaction:
    transaction = FinanceTransaction(
        save_game_id=save.id,
        team_id=team.id,
        season_number=save.season_number,
        week=save.current_week,
        category="contract_commitment",
        amount=0,
        balance_after=team.budget,
        note=f"{player_name} renewed for {years} year(s): {previous_wage:,}/wk to {new_wage:,}/wk.",
        created_at=datetime.now(timezone.utc),
    )
    session.add(transaction)
    session.flush()
    return transaction


def _latest_result_text(result: MatchResult | None, team: Team) -> str:
    if not result:
        return "No result logged yet."
    team_score = result.home_score if result.home_team_id == team.id else result.away_score
    opponent_score = result.away_score if result.home_team_id == team.id else result.home_score
    if team_score > opponent_score:
        return f"Last week brought a win ({team_score}-{opponent_score})."
    if team_score == opponent_score:
        return f"Last week ended level ({team_score}-{opponent_score})."
    return f"Last week brought a defeat ({team_score}-{opponent_score})."


def build_board_drivers(session: Session, save: SaveGame, team: Team, board_state: BoardState) -> list[str]:
    current_wages = _current_wages(session, team.id)
    wage_usage = current_wages / team.wage_budget if team.wage_budget else 0
    operating_cost = weekly_operating_cost(team, board_state)
    table = build_table(session, save)
    position = next((row.position for row in table.rows if row.team_id == team.id), len(table.rows))
    target = _objective_target_position(team.board_objective, len(table.rows))
    latest_result = session.exec(
        select(MatchResult)
        .where(MatchResult.save_game_id == save.id)
        .where(MatchResult.season_number == save.season_number)
        .where((MatchResult.home_team_id == team.id) | (MatchResult.away_team_id == team.id))
        .order_by(MatchResult.created_at.desc())
    ).first()

    drivers = [_latest_result_text(latest_result, team)]
    if position <= target:
        drivers.append(f"League position is on objective at #{position}.")
    elif position <= target + 2:
        drivers.append(f"League position has drifted to #{position} against a top-{target} brief.")
    else:
        drivers.append(f"Table pressure is growing at #{position} against a target of {target}.")

    if team.budget < operating_cost * 3:
        drivers.append("Cash reserves are thin for the next month of operations.")
    elif team.budget > operating_cost * 9:
        drivers.append("Cash reserves are strong enough to absorb short-term swings.")
    else:
        drivers.append("Cash reserves are workable but need attention.")

    if wage_usage >= 0.97:
        drivers.append("The wage bill is nearly at its ceiling.")
    elif wage_usage >= 0.9:
        drivers.append("The wage bill is healthy but offers limited flexibility.")
    else:
        drivers.append("The wage bill leaves room for moves.")

    if board_state.operating_focus == "performance":
        drivers.append("Operating focus is tilted toward performance support and extra running cost.")
    elif board_state.operating_focus == "commercial":
        drivers.append("Operating focus is tilted toward revenue protection and commercial lift.")
    else:
        drivers.append("Operating focus remains balanced between squad and cash flow.")
    return drivers[:5]


def _pressure_message(previous: str, current: str) -> tuple[str, str] | None:
    if previous == current:
        return None
    if current == "critical":
        return "Board pressure critical", "The board considers the club under significant pressure after the latest weekly review."
    if current == "watch":
        return "Board confidence slipping", "The weekly board review has moved the club onto a watch footing."
    return "Board backing improved", "Recent results and club management have steadied the board outlook."


def _apply_performance_focus_boost(session: Session, team: Team) -> None:
    players = session.exec(select(Player).where(Player.team_id == team.id)).all()
    for player in players:
        player.morale = min(99, player.morale + 1)
        if player.injury_weeks_remaining == 0:
            player.fitness = min(99, player.fitness + 1)
            player.fatigue = max(0, player.fatigue - 1)
        session.add(player)


def _update_board_confidence(
    session: Session,
    save: SaveGame,
    team: Team,
    board_state: BoardState,
    *,
    user_result_fixture_id: int | None,
) -> None:
    previous_pressure = board_state.pressure_state
    current_wages = _current_wages(session, team.id)
    wage_usage = current_wages / team.wage_budget if team.wage_budget else 0
    operating_cost = weekly_operating_cost(team, board_state)
    table = build_table(session, save)
    position = next((row.position for row in table.rows if row.team_id == team.id), len(table.rows))
    target = _objective_target_position(team.board_objective, len(table.rows))
    delta = 0

    if user_result_fixture_id:
        result = session.exec(select(MatchResult).where(MatchResult.fixture_id == user_result_fixture_id)).first()
        if result:
            team_score = result.home_score if result.home_team_id == team.id else result.away_score
            opponent_score = result.away_score if result.home_team_id == team.id else result.home_score
            margin = abs(team_score - opponent_score)
            if team_score > opponent_score:
                delta += 5 + (1 if margin >= 12 else 0)
            elif team_score == opponent_score:
                delta += 1
            else:
                delta -= 5 + (1 if margin >= 12 else 0)

    gap = position - target
    if gap <= 0:
        delta += 3
    elif gap == 1:
        delta -= 1
    elif gap == 2:
        delta -= 3
    else:
        delta -= 5

    if team.budget < operating_cost * 3:
        delta -= 4
    elif team.budget < operating_cost * 5:
        delta -= 2
    elif team.budget > operating_cost * 9:
        delta += 2

    if wage_usage > 0.97:
        delta -= 4
    elif wage_usage > 0.93:
        delta -= 2
    elif wage_usage < 0.84:
        delta += 1

    if board_state.operating_focus == "performance":
        delta += 1 if user_result_fixture_id else 0
        if team.budget < operating_cost * 5:
            delta -= 2
    elif board_state.operating_focus == "commercial":
        if team.budget < operating_cost * 5:
            delta += 2
        if wage_usage < 0.9:
            delta += 1

    board_state.confidence = _clamp(board_state.confidence + delta, 5, 95)
    board_state.pressure_state = pressure_state_for(board_state.confidence)
    board_state.updated_at = datetime.now(timezone.utc)
    session.add(board_state)

    message = _pressure_message(previous_pressure, board_state.pressure_state)
    if message:
        title, body = message
        session.add(
            InboxMessage(
                save_game_id=save.id,
                season_number=save.season_number,
                team_id=team.id,
                type="board",
                title=title,
                body=body,
                created_at=datetime.now(timezone.utc),
            )
        )


def process_user_weekly_finance(
    session: Session,
    save: SaveGame,
    user_team: Team,
    *,
    user_result_fixture_id: int | None,
) -> None:
    board_state = ensure_board_state(session, save, user_team)
    already_processed = session.exec(
        select(FinanceTransaction)
        .where(FinanceTransaction.save_game_id == save.id)
        .where(FinanceTransaction.team_id == user_team.id)
        .where(FinanceTransaction.season_number == save.season_number)
        .where(FinanceTransaction.week == save.current_week)
        .where(FinanceTransaction.category == "sponsor_income")
    ).first()
    if already_processed:
        return

    sponsor_income = weekly_sponsor_income(user_team, board_state)
    squad_wages = _current_wages(session, user_team.id)
    operating_cost = weekly_operating_cost(user_team, board_state)

    log_budget_transaction(
        session,
        save,
        user_team,
        category="sponsor_income",
        amount=sponsor_income,
        note="Weekly sponsor and commercial distributions cleared.",
    )
    log_budget_transaction(
        session,
        save,
        user_team,
        category="weekly_wages",
        amount=-squad_wages,
        note="Weekly senior squad payroll processed.",
    )
    log_budget_transaction(
        session,
        save,
        user_team,
        category="operating_cost",
        amount=-operating_cost,
        note=f"Operating focus: {board_state.operating_focus}.",
    )

    if user_result_fixture_id:
        fixture = session.get(Fixture, user_result_fixture_id)
        if fixture and fixture.home_team_id == user_team.id:
            result = session.get(MatchResult, fixture.result_id) if fixture.result_id else None
            gate = estimated_home_gate(user_team, board_state, result)
            log_budget_transaction(
                session,
                save,
                user_team,
                category="gate_receipts",
                amount=gate,
                note=f"Home gate receipts from {fixture.round_name}.",
            )

    if board_state.operating_focus == "performance":
        _apply_performance_focus_boost(session, user_team)

    _update_board_confidence(
        session,
        save,
        user_team,
        board_state,
        user_result_fixture_id=user_result_fixture_id,
    )


def apply_season_review_finance(
    session: Session,
    save: SaveGame,
    team: Team,
    *,
    verdict: str,
    budget_delta: int,
    final_position: int,
) -> None:
    board_state = ensure_board_state(session, save, team)
    actual_delta = max(2_000_000, team.budget + budget_delta) - team.budget
    log_budget_transaction(
        session,
        save,
        team,
        category="season_review",
        amount=actual_delta,
        note=f"Season review: {verdict} after finishing #{final_position}.",
        week=save.total_weeks,
    )

    verdict_delta = {
        "Outstanding season": 12,
        "Board pleased": 7,
        "Objective met": 3,
        "Below expectations": -8,
        "Major disappointment": -14,
    }.get(verdict, 0)
    board_state.confidence = _clamp(board_state.confidence + verdict_delta, 5, 95)
    board_state.pressure_state = pressure_state_for(board_state.confidence)
    board_state.updated_at = datetime.now(timezone.utc)
    session.add(board_state)


def _projected_balance_4_weeks(session: Session, save: SaveGame, team: Team, board_state: BoardState) -> int:
    recurring_net = weekly_sponsor_income(team, board_state) - _current_wages(session, team.id) - weekly_operating_cost(team, board_state)
    upcoming_home_fixtures = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == save.season_number)
        .where(Fixture.week >= save.current_week)
        .where(Fixture.week < save.current_week + 4)
        .where(Fixture.home_team_id == team.id)
        .where(Fixture.played.is_(False))
        .order_by(Fixture.week, Fixture.id)
    ).all()
    gate_projection = sum(estimated_home_gate(team, board_state) for _ in upcoming_home_fixtures)
    return team.budget + recurring_net * 4 + gate_projection


def _weekly_breakdown(transactions: list[FinanceTransaction]) -> list[FinanceWeekBreakdownRead]:
    weekly: dict[int, dict[str, int]] = defaultdict(lambda: {"income": 0, "expenses": 0})
    for transaction in transactions:
        bucket = weekly[transaction.week]
        if transaction.amount >= 0:
            bucket["income"] += transaction.amount
        else:
            bucket["expenses"] += abs(transaction.amount)
    weeks = sorted(weekly.keys())[-6:]
    return [
        FinanceWeekBreakdownRead(
            week=week,
            income=weekly[week]["income"],
            expenses=weekly[week]["expenses"],
            net=weekly[week]["income"] - weekly[week]["expenses"],
        )
        for week in weeks
    ]


def get_finance_overview(session: Session) -> FinanceOverviewResponse:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    board_state = session.exec(
        select(BoardState)
        .where(BoardState.save_game_id == save.id)
        .where(BoardState.team_id == user_team.id)
        .where(BoardState.season_number == save.season_number)
        .order_by(BoardState.id.desc())
    ).first()
    if not board_state:
        board_state = ensure_board_state(session, save, user_team)
        session.commit()
        session.refresh(board_state)
    transactions = session.exec(
        select(FinanceTransaction)
        .where(FinanceTransaction.save_game_id == save.id)
        .where(FinanceTransaction.team_id == user_team.id)
        .where(FinanceTransaction.season_number == save.season_number)
        .order_by(FinanceTransaction.created_at.desc(), FinanceTransaction.id.desc())
    ).all()
    current_wages = _current_wages(session, user_team.id)
    return FinanceOverviewResponse(
        save=build_save_summary(session, save),
        board=BoardStatusRead(
            objective=user_team.board_objective,
            confidence=board_state.confidence,
            pressure_state=board_state.pressure_state,
            operating_focus=board_state.operating_focus,
            drivers=build_board_drivers(session, save, user_team, board_state),
        ),
        summary=FinanceSummaryRead(
            transfer_budget=user_team.budget,
            wage_budget=user_team.wage_budget,
            current_wages=current_wages,
            remaining_wage_budget=max(0, user_team.wage_budget - current_wages),
            weekly_sponsor_income=weekly_sponsor_income(user_team, board_state),
            weekly_operating_cost=weekly_operating_cost(user_team, board_state),
            average_home_gate=estimated_home_gate(user_team, board_state),
            projected_balance_4_weeks=_projected_balance_4_weeks(session, save, user_team, board_state),
        ),
        recent_transactions=[_finance_transaction_read(transaction) for transaction in transactions[:10]],
        weekly_breakdown=_weekly_breakdown(list(reversed(transactions))),
    )


def update_finance_settings(session: Session, request: FinanceSettingsUpdateRequest) -> FinanceOverviewResponse:
    if request.operating_focus not in OPERATING_FOCUS_VALUES:
        raise HTTPException(status_code=400, detail="Invalid operating focus.")
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    board_state = ensure_board_state(session, save, user_team)
    board_state.operating_focus = request.operating_focus
    board_state.updated_at = datetime.now(timezone.utc)
    session.add(board_state)
    session.commit()
    session.refresh(board_state)
    return get_finance_overview(session)
