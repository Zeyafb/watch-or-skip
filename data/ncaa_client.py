"""NCAA basketball data client using ESPN API. Fetches George Mason games."""

import requests

GMU_TEAM_ID = "2244"
GMU_NAME = "George Mason Patriots"
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"


def get_games_for_date(date_str: str) -> list[dict]:
    """Fetch GMU games for a given date (YYYY-MM-DD).
    Returns a list of game dicts.
    """
    # ESPN date format: YYYYMMDD
    espn_date = date_str.replace("-", "")

    url = f"{ESPN_BASE}/scoreboard"
    resp = requests.get(url, params={"dates": espn_date, "groups": "50", "limit": 400}, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    games = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        team_names = [c["team"]["displayName"] for c in competitors]

        if not any("george mason" in n.lower() for n in team_names):
            continue

        status_name = comp.get("status", {}).get("type", {}).get("name", "")

        if status_name == "STATUS_FINAL":
            games.append(_build_game_data(comp, event))
        elif status_name == "STATUS_POSTPONED":
            gmu, opp = _split_teams(competitors)
            games.append({
                "status": "Postponed",
                "home_team": _team_name(competitors, "home"),
                "away_team": _team_name(competitors, "away"),
            })
        elif status_name == "STATUS_SCHEDULED":
            gmu, opp = _split_teams(competitors)
            games.append({
                "status": "Upcoming",
                "home_team": _team_name(competitors, "home"),
                "away_team": _team_name(competitors, "away"),
                "start_time_utc": event.get("date", ""),
                "gmu_home": gmu.get("homeAway") == "home",
            })

    return games


def get_upcoming_games(days: int = 7) -> list[dict]:
    """Get upcoming GMU games from team schedule. Used for the schedule view."""
    from datetime import datetime, timedelta

    url = f"{ESPN_BASE}/teams/{GMU_TEAM_ID}/schedule"
    # Determine current season (NCAA season spans two calendar years)
    now = datetime.now()
    season = now.year if now.month >= 9 else now.year
    resp = requests.get(url, params={"season": season}, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    cutoff = now + timedelta(days=days)
    upcoming = []
    for event in data.get("events", []):
        event_date_str = event.get("date", "")
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        # Convert to naive for comparison
        event_naive = event_date.replace(tzinfo=None)
        if event_naive < now or event_naive > cutoff:
            continue

        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        status_name = comp.get("status", {}).get("type", {}).get("name", "")
        gmu, opp = _split_teams(competitors)

        upcoming.append({
            "sport": "ncaa",
            "date": event_date_str,
            "home_team": _team_name(competitors, "home"),
            "away_team": _team_name(competitors, "away"),
            "gmu_home": gmu.get("homeAway") == "home" if gmu else False,
            "status": status_name,
        })

    return upcoming


def _build_game_data(comp: dict, event: dict) -> dict:
    """Build structured dict for a completed GMU game."""
    competitors = comp.get("competitors", [])
    gmu, opp = _split_teams(competitors)

    gmu_score_raw = gmu.get("score", "0")
    opp_score_raw = opp.get("score", "0")
    gmu_points = int(gmu_score_raw) if isinstance(gmu_score_raw, str) else int(gmu_score_raw.get("displayValue", "0") if isinstance(gmu_score_raw, dict) else gmu_score_raw)
    opp_points = int(opp_score_raw) if isinstance(opp_score_raw, str) else int(opp_score_raw.get("displayValue", "0") if isinstance(opp_score_raw, dict) else opp_score_raw)

    was_home = gmu.get("homeAway") == "home"

    return {
        "status": "Final",
        "home_team": _team_name(competitors, "home"),
        "away_team": _team_name(competitors, "away"),
        "gmu_points": gmu_points,
        "opponent_points": opp_points,
        "gmu_won": gmu_points > opp_points,
        "was_home_game": was_home,
    }


def _split_teams(competitors: list) -> tuple[dict, dict]:
    """Split competitors into GMU and opponent."""
    gmu = None
    opp = None
    for c in competitors:
        if "george mason" in c["team"]["displayName"].lower():
            gmu = c
        else:
            opp = c
    return gmu or {}, opp or {}


def _team_name(competitors: list, home_away: str) -> str:
    """Get team display name by home/away."""
    for c in competitors:
        if c.get("homeAway") == home_away:
            return c["team"]["displayName"]
    return "Unknown"
