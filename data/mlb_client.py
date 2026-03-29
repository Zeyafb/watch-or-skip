"""MLB data client using python-mlb-statsapi. Fetches completed Red Sox games."""

from mlbstatsapi import Mlb

RED_SOX_TEAM_ID = 111

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


def get_upcoming_games(days: int = 7) -> list[dict]:
    """Get upcoming Red Sox games for the next N days."""
    from datetime import datetime, timedelta

    start = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    schedule = mlb.get_schedule(start_date=start, end_date=end, team_id=RED_SOX_TEAM_ID)
    if schedule is None or not schedule.dates:
        return []

    upcoming = []
    for d in schedule.dates:
        for g in d.games:
            upcoming.append({
                "sport": "mlb",
                "date": g.game_date if hasattr(g, "game_date") else d.date,
                "home_team": g.teams.home.team.name,
                "away_team": g.teams.away.team.name,
                "red_sox_home": g.teams.home.team.id == RED_SOX_TEAM_ID,
                "status": g.status.detailed_state,
            })
    return upcoming


def _build_game_data(game) -> dict:
    """Build the structured dict for a completed game."""
    game_pk = game.game_pk
    home_team = game.teams.home.team.name
    away_team = game.teams.away.team.name
    home_id = game.teams.home.team.id
    away_id = game.teams.away.team.id

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

    # Tying run at the plate in 9th or later
    tying_run = _check_tying_run_at_plate(game_pk, red_sox_home)

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

    For each at-bat where Red Sox are batting in inning >= 9:
    - Count runners on base at the start of the at-bat
    - Max runs on a single hit = runners_on + 1 (batter)
    - Runs needed to tie = opponent_score - red_sox_score (at start of at-bat)
    - If runs_needed_to_tie <= runners_on + 1, the tying run is at the plate
    """
    pbp = mlb.get_game_play_by_play(game_pk)

    # Red Sox bat in "top" when away, "bottom" when home
    sox_batting_half = "bottom" if red_sox_home else "top"

    prev_away_score = 0
    prev_home_score = 0

    for i, play in enumerate(pbp.all_plays):
        # Track score at start of this at-bat from previous play
        if i > 0:
            prev_play = pbp.all_plays[i - 1]
            prev_away_score = prev_play.result.away_score or 0
            prev_home_score = prev_play.result.home_score or 0

        if play.about.inning < 9:
            continue
        if play.about.half_inning != sox_batting_half:
            continue

        # Score at start of this at-bat
        if red_sox_home:
            sox_score = prev_home_score
            opp_score = prev_away_score
        else:
            sox_score = prev_away_score
            opp_score = prev_home_score

        deficit = opp_score - sox_score
        if deficit <= 0:
            # Red Sox are tied or leading — tying run is moot, but the game
            # is close enough that this counts
            return True

        # Count runners on base
        runners_on = sum([
            1 if play.matchup.post_on_first else 0,
            1 if play.matchup.post_on_second else 0,
            1 if play.matchup.post_on_third else 0,
        ])

        max_runs_on_hit = runners_on + 1  # all runners + batter
        if deficit <= max_runs_on_hit:
            return True

    return False
