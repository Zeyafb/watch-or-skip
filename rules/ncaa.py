"""NCAA basketball rules engine for Watch or Skip decisions (GMU)."""


def evaluate(game: dict) -> tuple[str, str]:
    """Apply decision rules to a completed GMU game.
    Returns (verdict, reason) where verdict is 'YES' or 'NO'.

    Note: Matt watches all home games live. This only evaluates away games.
    If the game was a home game, returns a special 'HOME' verdict.
    """
    # Home game — Matt watches these live
    if game["was_home_game"]:
        return ("HOME", "Home game — auto watch")

    # 1. WIN
    if game["gmu_won"]:
        return ("YES", "GMU won on the road")

    # 2. DEFAULT
    return ("NO", "GMU lost on the road")
