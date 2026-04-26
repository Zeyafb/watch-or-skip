"""MLB data client using python-mlb-statsapi. Fetches completed Red Sox games."""

import requests
from mlbstatsapi import Mlb

RED_SOX_TEAM_ID = 111
RAW_API_BASE = "https://statsapi.mlb.com/api/v1"

mlb = Mlb()


def get_games_for_date(date_str: str) -> list[dict]:
    """Fetch all Red Sox games for a given date string (YYYY-MM-DD).
    Returns a list of game dicts (multiple for doubleheaders).
    """
    schedule = mlb.get_schedule(date=date_str, team_id=RED_SOX_TEAM_ID)
    if schedule is None or not schedule.dates:
        return []
    games = []
    for d in schedule.dates:
        for g in d.games:
            state = g.status.detailed_state
            if state == "Final":
                games.append(_build_game_data(g))
            elif state in ("Postponed", "Suspended", "Cancelled"):
                games.append({
                    "status": state,
                    "home_team": g.teams.home.team.name,
                    "away_team": g.teams.away.team.name,
                })
            else:
                # Upcoming / in-progress / game over / other
                games.append({
                    "status": "Upcoming",
                    "game_pk": g.game_pk,
                    "home_team": g.teams.home.team.name,
                    "away_team": g.teams.away.team.name,
                    "red_sox_home": g.teams.home.team.id == RED_SOX_TEAM_ID,
                    "start_time_utc": g.game_date if hasattr(g, "game_date") else "",
                })
    return games


def _build_game_data(game) -> dict:
    """Build the structured dict for a completed game."""
    game_pk = game.game_pk
    home_team = game.teams.home.team.name
    away_team = game.teams.away.team.name
    home_id = game.teams.home.team.id

    red_sox_home = home_id == RED_SOX_TEAM_ID

    # Linescore for final score and inning-by-inning data
    ls = mlb.get_game_line_score(game_pk)
    home_runs = ls.teams.home.runs or 0
    away_runs = ls.teams.away.runs or 0

    red_sox_runs = home_runs if red_sox_home else away_runs
    opponent_runs = away_runs if red_sox_home else home_runs
    red_sox_won = red_sox_runs > opponent_runs

    # Count innings played from linescore
    innings_played = len(ls.innings)
    went_extra_innings = innings_played > 9

    # Score entering bottom of 9th
    score_entering_bottom_9th = _get_score_entering_bottom_9th(ls, red_sox_home)

    # Tying run at the plate in 9th or later — never let a parse failure
    # take down the whole game card
    try:
        tying_run = _check_tying_run_at_plate(game_pk, red_sox_home)
    except Exception:
        tying_run = False

    return {
        "status": "Final",
        "game_pk": game_pk,
        "home_team": home_team,
        "away_team": away_team,
        "final_score": {
            "home_runs": home_runs,
            "away_runs": away_runs,
            "home_team": home_team,
            "away_team": away_team,
        },
        "red_sox_runs": red_sox_runs,
        "opponent_runs": opponent_runs,
        "red_sox_won": red_sox_won,
        "red_sox_home": red_sox_home,
        "innings_played": innings_played,
        "went_extra_innings": went_extra_innings,
        "score_entering_bottom_9th": score_entering_bottom_9th,
        "tying_run_at_plate_in_9th_plus": tying_run,
    }


def _get_score_entering_bottom_9th(ls, red_sox_home: bool) -> dict:
    """Reconstruct score entering bottom of 9th from linescore innings."""
    home_total = 0
    away_total = 0
    for inn in ls.innings:
        if inn.num < 9:
            home_total += inn.home.runs or 0
            away_total += inn.away.runs or 0
        elif inn.num == 9:
            # Add top of 9th runs (away bats top)
            away_total += inn.away.runs or 0
            break

    if red_sox_home:
        return {"red_sox": home_total, "opponent": away_total}
    else:
        return {"red_sox": away_total, "opponent": home_total}


def _check_tying_run_at_plate(game_pk: int, red_sox_home: bool) -> bool:
    """Check if the tying run came to the plate for the Red Sox in the 9th+.

    Uses the raw MLB Stats API to avoid pydantic validation failures in the
    mlbstatsapi library (which rejects the entire response if any single
    pitch event has unexpected fields, e.g. missing pitch type code).

    For each at-bat where Red Sox are batting in inning >= 9:
    - Count runners on base at the start of the at-bat
    - Max runs on a single hit = runners_on + 1 (batter)
    - Runs needed to tie = opponent_score - red_sox_score (at start of at-bat)
    - If runs_needed_to_tie <= runners_on + 1, the tying run is at the plate
    """
    plays = _get_plays_raw(game_pk)
    if plays is None:
        return False

    sox_batting_half = "bottom" if red_sox_home else "top"
    prev_away_score = 0
    prev_home_score = 0

    for i, play in enumerate(plays):
        # Track score at start of this at-bat from previous play
        if i > 0:
            prev_result = plays[i - 1].get("result", {})
            prev_away_score = prev_result.get("awayScore", 0) or 0
            prev_home_score = prev_result.get("homeScore", 0) or 0

        about = play.get("about", {})
        if about.get("inning", 0) < 9:
            continue
        if about.get("halfInning", "") != sox_batting_half:
            continue

        if red_sox_home:
            sox_score = prev_home_score
            opp_score = prev_away_score
        else:
            sox_score = prev_away_score
            opp_score = prev_home_score

        deficit = opp_score - sox_score
        if deficit <= 0:
            return True

        matchup = play.get("matchup", {})
        runners_on = sum([
            1 if matchup.get("postOnFirst") else 0,
            1 if matchup.get("postOnSecond") else 0,
            1 if matchup.get("postOnThird") else 0,
        ])

        max_runs_on_hit = runners_on + 1
        if deficit <= max_runs_on_hit:
            return True

    return False


def get_condensed_game_url(game_pk: int) -> str | None:
    """Find the 'Condensed Game' mp4 URL from the MLB content API.

    Works for any MLB game, including losses (which the Red Sox YouTube
    channel doesn't post full recaps for). Returns None if no condensed
    game is available yet (highlights take a few hours to publish).
    """
    try:
        resp = requests.get(
            f"{RAW_API_BASE}/game/{game_pk}/content",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    items = (
        data.get("highlights", {})
            .get("highlights", {})
            .get("items", [])
    )
    # Prefer "Condensed Game" — best 5-7 min recap with full game flow
    for clip in items:
        if "condensed game" in clip.get("title", "").lower():
            return _pick_mp4_url(clip)
    # Fallback: any "recap"-titled clip
    for clip in items:
        if "recap" in clip.get("title", "").lower():
            return _pick_mp4_url(clip)
    return None


def _pick_mp4_url(clip: dict) -> str | None:
    """Pick the best-quality mp4 URL from a highlight clip."""
    import re
    playbacks = clip.get("playbacks", [])
    candidates = [p for p in playbacks if p.get("name", "").startswith("mp4Avc")]
    if not candidates:
        candidates = [p for p in playbacks if "mp4" in p.get("url", "").lower()]
    if not candidates:
        return None
    # Pick highest bitrate — name like "mp4Avc1800K_640X360"
    candidates.sort(
        key=lambda p: int((re.search(r"(\d+)K", p.get("name", "")) or [None, "0"])[1]),
        reverse=True,
    )
    return candidates[0].get("url")


def _get_plays_raw(game_pk: int) -> list | None:
    """Fetch play-by-play via the raw MLB Stats API as a list of dicts.

    Returns None if the request fails entirely. Returns [] if the response
    is malformed but reachable.
    """
    try:
        resp = requests.get(
            f"{RAW_API_BASE}/game/{game_pk}/playByPlay",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("allPlays", [])
    except (requests.RequestException, ValueError):
        return None
