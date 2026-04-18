"""NHL data client using nhl-api-py. Fetches completed Capitals games."""

from nhlpy import NHLClient

CAPS_TEAM_ID = 15
CAPS_ABBREV = "WSH"

client = NHLClient()


def _full_team_name(team_data: dict) -> str:
    """Build full team name like 'Washington Capitals' from API data."""
    place = team_data.get("placeName", {})
    common = team_data.get("commonName", {})
    place_str = place.get("default", place) if isinstance(place, dict) else place
    common_str = common.get("default", common) if isinstance(common, dict) else common
    if place_str and common_str:
        return f"{place_str} {common_str}"
    return place_str or common_str or team_data.get("abbrev", "?")


def get_games_for_date(date_str: str) -> list[dict]:
    """Fetch all Capitals games for a given date string (YYYY-MM-DD).
    Returns a list of game dicts.
    """
    sched = client.schedule.daily_schedule(date=date_str)
    if not sched or "games" not in sched:
        return []

    games = []
    for g in sched["games"]:
        away_abbrev = g["awayTeam"]["abbrev"]
        home_abbrev = g["homeTeam"]["abbrev"]
        if away_abbrev != CAPS_ABBREV and home_abbrev != CAPS_ABBREV:
            continue

        state = g.get("gameState", "")
        home_name = _full_team_name(g["homeTeam"])
        away_name = _full_team_name(g["awayTeam"])

        if state in ("OFF", "FINAL"):
            games.append(_build_game_data(g))
        elif state in ("PPD",):
            games.append({
                "status": "Postponed",
                "home_team": home_name,
                "away_team": away_name,
            })
        else:
            # FUT, PRE, LIVE, CRIT, or any other state — show as upcoming
            games.append({
                "status": "Upcoming",
                "game_id": g.get("id"),
                "home_team": home_name,
                "away_team": away_name,
                "home_abbrev": home_abbrev,
                "away_abbrev": away_abbrev,
                "start_time_utc": g.get("startTimeUTC", ""),
                "caps_home": home_abbrev == CAPS_ABBREV,
            })

    return games


def _build_game_data(game: dict) -> dict:
    """Build structured dict for a completed Caps game."""
    game_id = game["id"]
    home_abbrev = game["homeTeam"]["abbrev"]
    away_abbrev = game["awayTeam"]["abbrev"]
    caps_home = home_abbrev == CAPS_ABBREV

    home_score = game["homeTeam"].get("score", 0)
    away_score = game["awayTeam"].get("score", 0)
    caps_goals = home_score if caps_home else away_score
    opponent_goals = away_score if caps_home else home_score

    home_name = _full_team_name(game["homeTeam"])
    away_name = _full_team_name(game["awayTeam"])

    # Period info for OT/shootout detection
    period_desc = game.get("periodDescriptor", {})
    period_number = period_desc.get("number", 3)
    period_type = period_desc.get("periodType", "REG")

    went_to_ot = period_number > 3 or period_type == "OT"
    went_to_shootout = period_type == "SO"

    # Get empty net goals from play-by-play
    opponent_en_goals = _count_opponent_empty_net_goals(game_id, caps_home)

    caps_won = caps_goals > opponent_goals
    true_margin = opponent_goals - opponent_en_goals - caps_goals

    return {
        "status": "Final",
        "game_id": game_id,
        "home_team": home_name,
        "away_team": away_name,
        "home_abbrev": home_abbrev,
        "away_abbrev": away_abbrev,
        "caps_home": caps_home,
        "caps_goals": caps_goals,
        "opponent_goals": opponent_goals,
        "caps_won": caps_won,
        "went_to_ot": went_to_ot,
        "went_to_shootout": went_to_shootout,
        "opponent_empty_net_goals": opponent_en_goals,
        "true_margin": true_margin,
    }


def _count_opponent_empty_net_goals(game_id: int, caps_home: bool) -> int:
    """Count goals scored by the opponent when the Caps goalie was pulled.

    goalieInNetId is the goalie of the team BEING SCORED ON.
    An empty net goal against the Caps = opponent scores AND goalieInNetId is None
    (meaning the Caps had no goalie in net).
    """
    pbp = client.game_center.play_by_play(game_id=str(game_id))
    if not pbp or "plays" not in pbp:
        return 0

    caps_team_id = pbp["homeTeam"]["id"] if caps_home else pbp["awayTeam"]["id"]

    count = 0
    for play in pbp["plays"]:
        if play.get("typeDescKey") != "goal":
            continue
        details = play.get("details", {})
        scoring_team = details.get("eventOwnerTeamId")
        goalie_in_net = details.get("goalieInNetId")

        # Opponent scored and Caps goalie was pulled (empty net)
        if scoring_team != caps_team_id and goalie_in_net is None:
            count += 1

    return count
