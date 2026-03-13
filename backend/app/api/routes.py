from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app.db.session import get_session
from backend.app.schemas.api import (
    AdvanceWeekResponse,
    ClubOption,
    ContractRenewRequest,
    DashboardResponse,
    FinanceOverviewResponse,
    FinanceSettingsUpdateRequest,
    FixtureListResponse,
    InboxResponse,
    LiveMatchHalftimeRequest,
    LiveMatchSnapshotRead,
    MatchResultRead,
    NewSaveRequest,
    NewSaveResponse,
    OffseasonStatusResponse,
    PerformanceOverviewResponse,
    PerformancePlanUpdateRequest,
    MedicalAssignmentUpdateRequest,
    RecruitmentResponse,
    SaveSummary,
    SeasonHistoryResponse,
    SeasonReviewResponse,
    SelectionRead,
    SelectionUpdateRequest,
    SquadResponse,
    TableResponse,
    TacticsRead,
    TacticsUpdateRequest,
    TeamOverviewRead,
    TransferBidRequest,
    TransferListResponse,
    YouthIntakeResponse,
)
from backend.app.services.career import advance_offseason, promote_youth_prospect
from backend.app.services.finance import get_finance_overview, update_finance_settings
from backend.app.services.performance import get_performance_overview, update_medical_assignment, update_performance_plan
from backend.app.services.game import (
    create_new_save,
    get_career_status,
    get_active_save_optional,
    get_club_overview,
    get_dashboard,
    get_fixtures,
    get_inbox,
    get_match_result,
    get_offseason_status,
    get_season_history,
    get_season_review,
    get_selection,
    get_squad,
    get_table,
    get_tactics,
    get_transfer_listings,
    get_youth_intake,
    list_available_clubs,
    update_selection,
    update_tactics,
)
from backend.app.services.recruitment import get_recruitment_board, start_scouting_target, toggle_shortlist_target
from backend.app.services.live_match import get_current_live_match, start_live_match, submit_halftime_changes, tick_live_match
from backend.app.services.progression import advance_week
from backend.app.services.transfers import make_transfer_bid, renew_contract


api_router = APIRouter()


@api_router.get("/saves/options", response_model=list[ClubOption])
def save_options() -> list[ClubOption]:
    return list_available_clubs()


@api_router.get("/save/current", response_model=SaveSummary | None)
def current_save(session: Session = Depends(get_session)) -> SaveSummary | None:
    save = get_active_save_optional(session)
    if not save:
        return None
    from backend.app.services.game import build_save_summary

    return build_save_summary(session, save)


@api_router.post("/saves", response_model=NewSaveResponse)
def new_save(request: NewSaveRequest, session: Session = Depends(get_session)) -> NewSaveResponse:
    return NewSaveResponse(save=create_new_save(session, request.team_id, request.name))


@api_router.get("/career/status", response_model=SaveSummary)
def career_status(session: Session = Depends(get_session)) -> SaveSummary:
    return get_career_status(session)


@api_router.get("/dashboard", response_model=DashboardResponse)
def dashboard(session: Session = Depends(get_session)) -> DashboardResponse:
    return get_dashboard(session)


@api_router.get("/finance", response_model=FinanceOverviewResponse)
def finance(session: Session = Depends(get_session)) -> FinanceOverviewResponse:
    return get_finance_overview(session)


@api_router.put("/finance/settings", response_model=FinanceOverviewResponse)
def finance_settings(request: FinanceSettingsUpdateRequest, session: Session = Depends(get_session)) -> FinanceOverviewResponse:
    return update_finance_settings(session, request)


@api_router.get("/performance", response_model=PerformanceOverviewResponse)
def performance(session: Session = Depends(get_session)) -> PerformanceOverviewResponse:
    return get_performance_overview(session)


@api_router.put("/performance/plan", response_model=PerformanceOverviewResponse)
def performance_plan(
    request: PerformancePlanUpdateRequest,
    session: Session = Depends(get_session),
) -> PerformanceOverviewResponse:
    return update_performance_plan(session, request)


@api_router.put("/performance/medical/{player_id}", response_model=PerformanceOverviewResponse)
def performance_medical(
    player_id: int,
    request: MedicalAssignmentUpdateRequest,
    session: Session = Depends(get_session),
) -> PerformanceOverviewResponse:
    return update_medical_assignment(session, player_id, request)


@api_router.get("/club", response_model=TeamOverviewRead)
def club(session: Session = Depends(get_session)) -> TeamOverviewRead:
    return get_club_overview(session)


@api_router.get("/squad", response_model=SquadResponse)
def squad(session: Session = Depends(get_session)) -> SquadResponse:
    return get_squad(session)


@api_router.get("/tactics", response_model=TacticsRead)
def tactics(session: Session = Depends(get_session)) -> TacticsRead:
    return get_tactics(session)


@api_router.put("/tactics", response_model=TacticsRead)
def tactics_update(request: TacticsUpdateRequest, session: Session = Depends(get_session)) -> TacticsRead:
    return update_tactics(session, request)


@api_router.get("/selection", response_model=SelectionRead)
def selection(session: Session = Depends(get_session)) -> SelectionRead:
    return get_selection(session)


@api_router.put("/selection", response_model=SelectionRead)
def selection_update(request: SelectionUpdateRequest, session: Session = Depends(get_session)) -> SelectionRead:
    return update_selection(session, request)


@api_router.get("/fixtures", response_model=FixtureListResponse)
def fixtures(session: Session = Depends(get_session)) -> FixtureListResponse:
    return get_fixtures(session)


@api_router.post("/advance-week", response_model=AdvanceWeekResponse)
def advance(session: Session = Depends(get_session)) -> AdvanceWeekResponse:
    return advance_week(session)


@api_router.get("/live-match/current", response_model=LiveMatchSnapshotRead | None)
def current_live_match(session: Session = Depends(get_session)) -> LiveMatchSnapshotRead | None:
    return get_current_live_match(session)


@api_router.post("/live-match/start", response_model=LiveMatchSnapshotRead)
def live_match_start(session: Session = Depends(get_session)) -> LiveMatchSnapshotRead:
    return start_live_match(session)


@api_router.post("/live-match/tick", response_model=LiveMatchSnapshotRead)
def live_match_tick(session: Session = Depends(get_session)) -> LiveMatchSnapshotRead:
    return tick_live_match(session)


@api_router.post("/live-match/halftime", response_model=LiveMatchSnapshotRead)
def live_match_halftime(request: LiveMatchHalftimeRequest, session: Session = Depends(get_session)) -> LiveMatchSnapshotRead:
    return submit_halftime_changes(session, request)


@api_router.get("/season/review", response_model=SeasonReviewResponse)
def season_review(session: Session = Depends(get_session)) -> SeasonReviewResponse:
    return get_season_review(session)


@api_router.get("/offseason/status", response_model=OffseasonStatusResponse)
def offseason_status(session: Session = Depends(get_session)) -> OffseasonStatusResponse:
    return get_offseason_status(session)


@api_router.post("/offseason/advance", response_model=SaveSummary)
def offseason_advance(session: Session = Depends(get_session)) -> SaveSummary:
    return advance_offseason(session)


@api_router.get("/youth-intake", response_model=YouthIntakeResponse)
def youth_intake(session: Session = Depends(get_session)) -> YouthIntakeResponse:
    return get_youth_intake(session)


@api_router.post("/youth-intake/{prospect_id}/promote")
def youth_promote(prospect_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    return promote_youth_prospect(session, prospect_id)


@api_router.get("/history/seasons", response_model=SeasonHistoryResponse)
def history_seasons(session: Session = Depends(get_session)) -> SeasonHistoryResponse:
    return get_season_history(session)


@api_router.get("/table", response_model=TableResponse)
def table(session: Session = Depends(get_session)) -> TableResponse:
    return get_table(session)


@api_router.get("/transfers", response_model=TransferListResponse)
def transfers(session: Session = Depends(get_session)) -> TransferListResponse:
    return get_transfer_listings(session)


@api_router.get("/recruitment", response_model=RecruitmentResponse)
def recruitment(session: Session = Depends(get_session)) -> RecruitmentResponse:
    return get_recruitment_board(session)


@api_router.post("/recruitment/scouting/{player_id}")
def recruitment_scout(player_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    return start_scouting_target(session, player_id)


@api_router.post("/recruitment/shortlist/{player_id}")
def recruitment_shortlist(player_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    return toggle_shortlist_target(session, player_id)


@api_router.post("/transfers/{listing_id}/bid")
def transfer_bid(listing_id: int, request: TransferBidRequest, session: Session = Depends(get_session)) -> dict[str, str]:
    return make_transfer_bid(session, listing_id, request.amount)


@api_router.post("/contracts/{player_id}/renew")
def contract_renew(player_id: int, request: ContractRenewRequest, session: Session = Depends(get_session)) -> dict[str, str]:
    return renew_contract(session, player_id, request.years, request.weekly_wage)


@api_router.get("/inbox", response_model=InboxResponse)
def inbox(session: Session = Depends(get_session)) -> InboxResponse:
    return get_inbox(session)


@api_router.get("/matches/{fixture_id}", response_model=MatchResultRead)
def match_result(fixture_id: int, session: Session = Depends(get_session)) -> MatchResultRead:
    return get_match_result(session, fixture_id)
