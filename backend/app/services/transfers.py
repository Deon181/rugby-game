from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.models.entities import InboxMessage, Player, Team, TeamSelection, TransferListing
from backend.app.services.game import get_active_save, get_user_team
from backend.app.services.selection import build_best_selection


def make_transfer_bid(session: Session, listing_id: int, amount: int) -> dict[str, str]:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    listing = session.exec(
        select(TransferListing)
        .where(TransferListing.save_game_id == save.id)
        .where(TransferListing.season_number == save.season_number)
        .where(TransferListing.id == listing_id)
        .where(TransferListing.is_active.is_(True))
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Transfer listing not found.")

    player = session.get(Player, listing.player_id)
    if player.team_id == user_team.id:
        raise HTTPException(status_code=400, detail="Player already belongs to your club.")

    team_players = session.exec(select(Player).where(Player.team_id == user_team.id)).all()
    current_wages = sum(candidate.wage for candidate in team_players)
    if amount < int(listing.asking_price * 0.92):
        raise HTTPException(status_code=400, detail="Bid is too low to be considered.")
    if amount > user_team.budget:
        raise HTTPException(status_code=400, detail="Insufficient transfer budget.")
    if current_wages + player.wage > user_team.wage_budget:
        raise HTTPException(status_code=400, detail="Insufficient wage budget.")

    seller = session.get(Team, player.team_id) if player.team_id is not None else None
    user_team.budget -= amount
    if seller:
        seller.budget += amount
    player.team_id = user_team.id
    player.morale = min(92, player.morale + 4)
    listing.is_active = False

    impacted_teams = {user_team.id}
    if seller:
        impacted_teams.add(seller.id)
    for team_id in impacted_teams:
        selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team_id)).first()
        team_players = session.exec(select(Player).where(Player.team_id == team_id)).all()
        best_selection = build_best_selection(team_players)
        selection.starting_lineup = [slot.model_dump() for slot in best_selection.starting_lineup]
        selection.bench_player_ids = best_selection.bench_player_ids
        selection.captain_id = best_selection.captain_id
        selection.goal_kicker_id = best_selection.goal_kicker_id
        session.add(selection)

    previous_club = seller.name if seller else "the free-agent market"
    body = f"{player.first_name} {player.last_name} joins from {previous_club} for {amount:,}."
    session.add(
        InboxMessage(
            save_game_id=save.id,
            season_number=save.season_number,
            team_id=user_team.id,
            type="transfer",
            title="Transfer completed",
            body=body,
            related_player_id=player.id,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.add(user_team)
    if seller:
        session.add(seller)
    session.add(player)
    session.add(listing)
    session.commit()
    return {"status": "accepted", "message": body}


def renew_contract(session: Session, player_id: int, years: int, weekly_wage: int) -> dict[str, str]:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    player = session.exec(select(Player).where(Player.id == player_id).where(Player.team_id == user_team.id)).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found at your club.")
    squad = session.exec(select(Player).where(Player.team_id == user_team.id)).all()
    current_wages = sum(candidate.wage for candidate in squad) - player.wage
    if current_wages + weekly_wage > user_team.wage_budget:
        raise HTTPException(status_code=400, detail="Renewal exceeds wage budget.")
    if weekly_wage < int(player.wage * 0.95):
        raise HTTPException(status_code=400, detail="Offer is below the player's current expectations.")

    player.wage = weekly_wage
    player.contract_years_remaining = years
    player.contract_last_renewed_season = save.season_number
    player.morale = min(95, player.morale + 6)
    session.add(player)
    session.add(
        InboxMessage(
            save_game_id=save.id,
            season_number=save.season_number,
            team_id=user_team.id,
            type="contract",
            title="Contract renewed",
            body=f"{player.first_name} {player.last_name} signs a new {years}-year deal at {weekly_wage:,} per week.",
            related_player_id=player.id,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    return {"status": "accepted", "message": f"Renewed {player.first_name} {player.last_name}'s contract."}
