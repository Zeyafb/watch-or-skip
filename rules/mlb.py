"""MLB rules engine for Watch or Skip decisions."""


def evaluate(game: dict) -> tuple[str, str]:
    """Apply decision rules to a completed Red Sox game.
    Returns (verdict, reason) where verdict is 'YES' or 'NO'.
    Rules are applied in strict priority order — first match wins.
    """
    # 1. SHUTOUT OVERRIDE
    if game["red_sox_runs"] == 0:
        return ("NO", "Shutout — Red Sox scored 0 runs")

    # 2. WIN
    if game["red_sox_won"]:
        return ("YES", "Red Sox won")

    # 3. EXTRA INNINGS
    if game["went_extra_innings"]:
        return ("YES", "Game went to extra innings")

    # 4. CLOSE ENTERING BOTTOM 9TH (only when Red Sox are home)
    if game["red_sox_home"]:
        score = game["score_entering_bottom_9th"]
        if score["red_sox"] >= score["opponent"]:
            return ("YES", "Red Sox were tied or winning entering the bottom of the 9th")

    # 5. TYING RUN AT THE PLATE
    if game["tying_run_at_plate_in_9th_plus"]:
        return ("YES", "Tying run came to the plate in the 9th or later")

    # 6. DEFAULT
    return ("NO", "Loss without drama")
