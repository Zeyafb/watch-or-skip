"""NHL rules engine for Watch or Skip decisions."""


def evaluate(game: dict) -> tuple[str, str]:
    """Apply decision rules to a completed Capitals game.
    Returns (verdict, reason) where verdict is 'YES' or 'NO'.
    Rules are applied in strict priority order — first match wins.
    """
    # 1. OT OR SHOOTOUT (always worth watching regardless of outcome)
    if game["went_to_ot"] or game["went_to_shootout"]:
        suffix = "Shootout" if game["went_to_shootout"] else "OT"
        return ("YES", f"Game went to {suffix}")

    # 2. CAPS WIN
    if game["caps_won"]:
        return ("YES", "Capitals won")

    # 3. SHUTOUT LOSS IN REGULATION
    if game["caps_goals"] == 0:
        return ("NO", "Shutout loss in regulation")

    # 4. CLOSE LOSS (one-goal game excluding empty netters)
    if game["true_margin"] <= 1:
        return ("YES", "One-goal loss (excluding empty netters)")

    # 5. DEFAULT
    return ("NO", "Loss by 2+ real goals")
