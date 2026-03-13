from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.core.constants import (
    CLEARANCE_STATUSES,
    CONTACT_LEVELS,
    MEDICAL_ALERT_FATIGUE,
    PERFORMANCE_INTENSITIES,
    REHAB_MODES,
    TRAINING_FOCUSES,
)
from backend.app.models.entities import Player, PlayerMedicalAssignment, SaveGame, Team, TeamTactics, WeeklyPerformancePlan
from backend.app.schemas.api import (
    MedicalAssignmentUpdateRequest,
    MedicalBoardPlayerRead,
    PerformanceOverviewResponse,
    PerformancePlanRead,
    PerformancePlanUpdateRequest,
    StaffEffectSummaryRead,
)
from backend.app.services.game import build_save_summary, get_active_save, get_user_team


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _plan_query(session: Session, save: SaveGame, team_id: int, week: int):
    return (
        select(WeeklyPerformancePlan)
        .where(WeeklyPerformancePlan.save_game_id == save.id)
        .where(WeeklyPerformancePlan.team_id == team_id)
        .where(WeeklyPerformancePlan.season_number == save.season_number)
        .where(WeeklyPerformancePlan.week == week)
        .order_by(WeeklyPerformancePlan.id.desc())
    )


def _assignment_query(session: Session, save: SaveGame, team_id: int, week: int):
    return (
        select(PlayerMedicalAssignment)
        .where(PlayerMedicalAssignment.save_game_id == save.id)
        .where(PlayerMedicalAssignment.team_id == team_id)
        .where(PlayerMedicalAssignment.season_number == save.season_number)
        .where(PlayerMedicalAssignment.week == week)
        .order_by(PlayerMedicalAssignment.id.desc())
    )


def _tactics_for_team(session: Session, team_id: int) -> TeamTactics:
    return session.exec(select(TeamTactics).where(TeamTactics.team_id == team_id)).first()


def recovery_bonus(team: Team) -> int:
    return max(0, round((team.staff_fitness - 68) / 6))


def injury_risk_multiplier(team: Team, contact_level: str = "balanced") -> float:
    contact_modifier = 0.85 if contact_level == "low" else 1.2 if contact_level == "high" else 1.0
    staff_modifier = max(0.82, 1 - (team.staff_fitness - 68) / 320)
    return round(contact_modifier * staff_modifier, 2)


def rehab_bonus(team: Team) -> int:
    return 1 if team.staff_fitness >= 76 else 0


def staff_effect_summary(team: Team, plan: WeeklyPerformancePlan) -> StaffEffectSummaryRead:
    return StaffEffectSummaryRead(
        fitness_staff_rating=team.staff_fitness,
        recovery_bonus=recovery_bonus(team),
        injury_risk_multiplier=injury_risk_multiplier(team, plan.contact_level),
        rehab_bonus=rehab_bonus(team),
    )


def ensure_weekly_performance_plan(session: Session, save: SaveGame, team: Team, *, week: int | None = None) -> WeeklyPerformancePlan:
    target_week = save.current_week if week is None else week
    existing = session.exec(_plan_query(session, save, team.id, target_week)).first()
    if existing:
        return existing

    previous = None
    if target_week > 1:
        previous = session.exec(_plan_query(session, save, team.id, target_week - 1)).first()
    tactics = _tactics_for_team(session, team.id)
    plan = WeeklyPerformancePlan(
        save_game_id=save.id,
        team_id=team.id,
        season_number=save.season_number,
        week=target_week,
        focus=previous.focus if previous else tactics.training_focus,
        intensity=previous.intensity if previous else "balanced",
        contact_level=previous.contact_level if previous else "balanced",
        prepared=target_week == 1,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(plan)
    session.flush()
    return plan


def sync_tactics_training_focus(session: Session, team: Team, focus: str) -> None:
    tactics = _tactics_for_team(session, team.id)
    tactics.training_focus = focus
    session.add(tactics)


def carry_forward_performance_plan(session: Session, save: SaveGame, team: Team) -> None:
    if save.current_week > save.total_weeks:
        return
    plan = ensure_weekly_performance_plan(session, save, team)
    plan.prepared = False if save.current_week > 1 else True
    plan.updated_at = _now()
    sync_tactics_training_focus(session, team, plan.focus)
    session.add(plan)


def _create_assignment(
    session: Session,
    save: SaveGame,
    team: Team,
    player: Player,
    *,
    rehab_mode: str,
    clearance_status: str,
    return_watch_weeks: int = 0,
    week: int | None = None,
) -> PlayerMedicalAssignment:
    assignment = PlayerMedicalAssignment(
        save_game_id=save.id,
        team_id=team.id,
        season_number=save.season_number,
        week=week or save.current_week,
        player_id=player.id,
        rehab_mode=rehab_mode,
        clearance_status=clearance_status,
        return_watch_weeks=return_watch_weeks,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(assignment)
    session.flush()
    return assignment


def ensure_week_medical_assignments(
    session: Session,
    save: SaveGame,
    team: Team,
    *,
    week: int | None = None,
) -> list[PlayerMedicalAssignment]:
    target_week = save.current_week if week is None else week
    existing = session.exec(_assignment_query(session, save, team.id, target_week)).all()
    assignments_by_player = {assignment.player_id: assignment for assignment in existing}
    players = session.exec(select(Player).where(Player.team_id == team.id).order_by(Player.overall_rating.desc())).all()

    for player in players:
        assignment = assignments_by_player.get(player.id)
        if player.injury_weeks_remaining > 0:
            if assignment:
                assignment.clearance_status = "out"
                assignment.updated_at = _now()
                session.add(assignment)
            else:
                assignments_by_player[player.id] = _create_assignment(
                    session,
                    save,
                    team,
                    player,
                    rehab_mode="standard",
                    clearance_status="out",
                    week=target_week,
                )
        elif player.fatigue >= MEDICAL_ALERT_FATIGUE and not assignment:
            assignments_by_player[player.id] = _create_assignment(
                session,
                save,
                team,
                player,
                rehab_mode="standard",
                clearance_status="full",
                week=target_week,
            )

    return list(assignments_by_player.values())


def medical_assignment_map(
    session: Session,
    save: SaveGame,
    team: Team,
    *,
    week: int | None = None,
) -> dict[int, PlayerMedicalAssignment]:
    assignments = ensure_week_medical_assignments(session, save, team, week=week)
    return {assignment.player_id: assignment for assignment in assignments}


def selection_blocked_player_ids(session: Session, save: SaveGame, team: Team, *, week: int | None = None) -> set[int]:
    target_week = save.current_week if week is None else week
    assignments = session.exec(_assignment_query(session, save, team.id, target_week)).all()
    return {assignment.player_id for assignment in assignments if assignment.clearance_status == "out"}


def mark_recent_return(session: Session, save: SaveGame, team: Team, player: Player) -> PlayerMedicalAssignment:
    assignment = session.exec(_assignment_query(session, save, team.id, save.current_week)).all()
    assignment_map = {item.player_id: item for item in assignment}
    existing = assignment_map.get(player.id)
    if existing:
        existing.clearance_status = "managed"
        existing.return_watch_weeks = 1
        existing.updated_at = _now()
        session.add(existing)
        return existing
    return _create_assignment(
        session,
        save,
        team,
        player,
        rehab_mode="standard",
        clearance_status="managed",
        return_watch_weeks=1,
    )


def current_user_performance_state(session: Session) -> tuple[SaveGame, Team, WeeklyPerformancePlan, list[PlayerMedicalAssignment]]:
    save = get_active_save(session)
    team = get_user_team(session, save)
    plan = ensure_weekly_performance_plan(session, save, team)
    assignments = ensure_week_medical_assignments(session, save, team)
    return save, team, plan, assignments


def _medical_note(player: Player, assignment: PlayerMedicalAssignment) -> str:
    if player.injury_weeks_remaining > 0:
        if assignment.rehab_mode == "physio":
            return "Physio block speeds recovery and boosts return fitness."
        if assignment.rehab_mode == "accelerated":
            return "Accelerated rehab shortens the timeline but risks a flatter return."
        return "Standard rehab keeps recovery steady."
    if assignment.return_watch_weeks > 0:
        if assignment.clearance_status == "out":
            return "Held out for one more controlled week."
        if assignment.clearance_status == "managed":
            return "Managed return: selection allowed with extra fatigue and injury risk."
        return "Fully cleared for normal use."
    return "High fatigue watch. Medical planning can lighten the load."


def _medical_entry(player: Player, assignment: PlayerMedicalAssignment, group: str) -> MedicalBoardPlayerRead:
    return MedicalBoardPlayerRead(
        player_id=player.id,
        player_name=f"{player.first_name} {player.last_name}",
        primary_position=player.primary_position,
        overall_rating=player.overall_rating,
        fitness=player.fitness,
        fatigue=player.fatigue,
        morale=player.morale,
        injury_status=player.injury_status,
        injury_weeks_remaining=player.injury_weeks_remaining,
        rehab_mode=assignment.rehab_mode,
        clearance_status=assignment.clearance_status,
        return_watch_weeks=assignment.return_watch_weeks,
        group=group,
        note=_medical_note(player, assignment),
    )


def get_performance_overview(session: Session) -> PerformanceOverviewResponse:
    from backend.app.services.progression import apply_between_week_recovery

    save = get_active_save(session)
    team = get_user_team(session, save)
    if save.phase == "in_season" and apply_between_week_recovery(session, save):
        session.commit()
        save = get_active_save(session)
        team = get_user_team(session, save)

    plan = ensure_weekly_performance_plan(session, save, team)
    sync_tactics_training_focus(session, team, plan.focus)
    assignments = ensure_week_medical_assignments(session, save, team)
    players_by_id = {
        player.id: player for player in session.exec(select(Player).where(Player.team_id == team.id).order_by(Player.overall_rating.desc())).all()
    }
    medical_board = [
        _medical_entry(players_by_id[assignment.player_id], assignment, "return" if assignment.return_watch_weeks > 0 else "injury")
        for assignment in assignments
        if assignment.player_id in players_by_id and (
            players_by_id[assignment.player_id].injury_weeks_remaining > 0
            or assignment.return_watch_weeks > 0
        )
    ]
    fatigue_watch = [
        _medical_entry(players_by_id[assignment.player_id], assignment, "fatigue")
        for assignment in assignments
        if assignment.player_id in players_by_id and players_by_id[assignment.player_id].fatigue >= MEDICAL_ALERT_FATIGUE
    ]
    session.commit()
    return PerformanceOverviewResponse(
        save=build_save_summary(session, save),
        plan=PerformancePlanRead(
            focus=plan.focus,
            intensity=plan.intensity,
            contact_level=plan.contact_level,
        ),
        fatigue_watch=fatigue_watch,
        medical_board=medical_board,
        staff_effects=staff_effect_summary(team, plan),
    )


def update_performance_plan(session: Session, request: PerformancePlanUpdateRequest) -> PerformanceOverviewResponse:
    if request.focus not in TRAINING_FOCUSES:
        raise HTTPException(status_code=400, detail="Invalid performance focus.")
    if request.intensity not in PERFORMANCE_INTENSITIES:
        raise HTTPException(status_code=400, detail="Invalid training intensity.")
    if request.contact_level not in CONTACT_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid contact level.")

    save = get_active_save(session)
    team = get_user_team(session, save)
    plan = ensure_weekly_performance_plan(session, save, team)
    plan.focus = request.focus
    plan.intensity = request.intensity
    plan.contact_level = request.contact_level
    plan.updated_at = _now()
    sync_tactics_training_focus(session, team, request.focus)
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return get_performance_overview(session)


def update_medical_assignment(
    session: Session,
    player_id: int,
    request: MedicalAssignmentUpdateRequest,
) -> PerformanceOverviewResponse:
    if request.rehab_mode and request.rehab_mode not in REHAB_MODES:
        raise HTTPException(status_code=400, detail="Invalid rehab mode.")
    if request.clearance_status and request.clearance_status not in CLEARANCE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid clearance status.")

    save = get_active_save(session)
    team = get_user_team(session, save)
    player = session.exec(select(Player).where(Player.id == player_id).where(Player.team_id == team.id)).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found at your club.")

    plan = ensure_weekly_performance_plan(session, save, team)
    assignment_map = medical_assignment_map(session, save, team)
    assignment = assignment_map.get(player.id)
    if not assignment:
        assignment = _create_assignment(
            session,
            save,
            team,
            player,
            rehab_mode="standard",
            clearance_status="out" if player.injury_weeks_remaining > 0 else "full",
        )

    if request.rehab_mode:
        assignment.rehab_mode = request.rehab_mode
    if request.clearance_status:
        if player.injury_weeks_remaining > 0 and request.clearance_status != "out":
            raise HTTPException(status_code=400, detail="Injured players cannot be medically cleared yet.")
        assignment.clearance_status = request.clearance_status
    assignment.updated_at = _now()
    if player.injury_weeks_remaining > 0:
        assignment.clearance_status = "out"
    if assignment.return_watch_weeks <= 0 and player.injury_weeks_remaining == 0 and player.fatigue < MEDICAL_ALERT_FATIGUE:
        assignment.return_watch_weeks = 0
    session.add(assignment)
    sync_tactics_training_focus(session, team, plan.focus)
    session.commit()
    return get_performance_overview(session)
