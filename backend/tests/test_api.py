def new_save_payload(template_team_id: int = 1, club_name: str = "Harbour City RFC", club_short_name: str = "HCR"):
    return {
        "template_team_id": template_team_id,
        "club_name": club_name,
        "club_short_name": club_short_name,
        "name": "API Save",
    }


def test_create_save_and_fetch_dashboard(client):
    current = client.get("/api/save/current")
    assert current.status_code == 200
    assert current.json() is None

    create = client.post("/api/saves", json=new_save_payload())
    assert create.status_code == 200
    payload = create.json()
    assert payload["save"]["current_week"] == 1
    assert payload["save"]["phase"] == "in_season"
    assert payload["save"]["user_team_name"] == "Harbour City RFC"
    assert payload["onboarding"]["team"]["name"] == "Harbour City RFC"
    assert payload["onboarding"]["team"]["short_name"] == "HCR"
    assert payload["onboarding"]["squad_summary"]["player_count"] == 30
    assert len(payload["onboarding"]["players"]) == 30
    assert payload["onboarding"]["featured_players"]
    assert payload["onboarding"]["next_fixture"] is not None

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["team"]["name"] == "Harbour City RFC"


def test_update_tactics_and_advance_week(client):
    client.post("/api/saves", json=new_save_payload())
    tactics = client.get("/api/tactics")
    payload = tactics.json()
    payload["attacking_style"] = "expansive"
    payload["ruck_commitment"] = "high"

    updated = client.put("/api/tactics", json=payload)
    assert updated.status_code == 200
    assert updated.json()["attacking_style"] == "expansive"

    started = client.post("/api/live-match/start")
    assert started.status_code == 200
    assert started.json()["status"] == "first_half"

    current = started.json()
    while current["status"] != "full_time":
        if current["status"] == "halftime":
            halftime = client.post(
                "/api/live-match/halftime",
                json={
                    "tactics": current["user_tactics"],
                    "substitutions": [],
                    "captain_id": current["user_selection"]["captain_id"],
                    "goal_kicker_id": current["user_selection"]["goal_kicker_id"],
                },
            )
            assert halftime.status_code == 200
            current = halftime.json()
        else:
            tick = client.post("/api/live-match/tick")
            assert tick.status_code == 200
            current = tick.json()

    assert current["result"] is not None
    assert current["save"]["phase"] == "in_season"

    table = client.get("/api/table")
    assert table.status_code == 200
    assert len(table.json()["rows"]) == 10


def test_offseason_endpoints_roll_into_new_season(client):
    client.post(
        "/api/saves",
        json={
            "template_team_id": 1,
            "club_name": "Cape Meridian RFC",
            "club_short_name": "CMR",
            "name": "Career Save",
        },
    )
    for _ in range(18):
        current = client.post("/api/live-match/start")
        assert current.status_code == 200
        snapshot = current.json()
        while snapshot["status"] != "full_time":
            if snapshot["status"] == "halftime":
                response = client.post(
                    "/api/live-match/halftime",
                    json={
                        "tactics": snapshot["user_tactics"],
                        "substitutions": [],
                        "captain_id": snapshot["user_selection"]["captain_id"],
                        "goal_kicker_id": snapshot["user_selection"]["goal_kicker_id"],
                    },
                )
            else:
                response = client.post("/api/live-match/tick")
            assert response.status_code == 200
            snapshot = response.json()

    career = client.get("/api/career/status")
    assert career.status_code == 200
    assert career.json()["phase"] == "season_review"

    review = client.get("/api/season/review")
    assert review.status_code == 200

    step_1 = client.post("/api/offseason/advance")
    assert step_1.status_code == 200
    assert step_1.json()["offseason_step"] == "contracts"

    step_2 = client.post("/api/offseason/advance")
    assert step_2.status_code == 200
    assert step_2.json()["offseason_step"] == "youth_intake"

    youth = client.get("/api/youth-intake")
    assert youth.status_code == 200
    assert youth.json()["prospects"]

    step_3 = client.post("/api/offseason/advance")
    assert step_3.status_code == 200
    assert step_3.json()["offseason_step"] == "rollover"

    step_4 = client.post("/api/offseason/advance")
    assert step_4.status_code == 200
    assert step_4.json()["phase"] == "in_season"
    assert step_4.json()["season_number"] == 2


def test_create_save_rejects_duplicate_club_identity(client):
    response = client.post(
        "/api/saves",
        json={
            "template_team_id": 1,
            "club_name": "Kingsport Admirals",
            "club_short_name": "NEW",
            "name": "Duplicate Save",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Club name must be unique in the league."
