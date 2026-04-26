"""Highlight video lookups for embedding in SKIP cards.

- NHL: NHL's public score endpoint exposes recap/condensed game URLs
       which point to Brightcove videos (no auth needed)

MLB highlight lookup lives in mlb_client.get_condensed_game_url()
since it uses the MLB Stats API content endpoint directly.
"""

import re
import requests
from datetime import date

NHL_BRIGHTCOVE_ACCOUNT = "6415718365001"


def find_caps_recap_iframe(game_date: date) -> str | None:
    """Find the NHL three-minute recap for the Caps game on game_date.

    Returns a Brightcove iframe URL ready for embedding, or None if no
    Caps game / no recap available yet.
    """
    try:
        resp = requests.get(
            f"https://api-web.nhle.com/v1/score/{game_date.strftime('%Y-%m-%d')}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    for g in data.get("games", []):
        if g.get("awayTeam", {}).get("abbrev") != "WSH" and g.get("homeTeam", {}).get("abbrev") != "WSH":
            continue
        recap_path = g.get("threeMinRecap") or g.get("condensedGame")
        if not recap_path:
            return None
        # Extract Brightcove video ID from end of path:
        # "/video/pit-at-wsh-recap-6392985837112" → "6392985837112"
        m = re.search(r"-(\d{10,})$", recap_path)
        if not m:
            return None
        video_id = m.group(1)
        return (
            f"https://players.brightcove.net/{NHL_BRIGHTCOVE_ACCOUNT}/"
            f"default_default/index.html?videoId={video_id}"
        )

    return None
