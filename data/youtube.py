"""Highlight video lookups for embedding in SKIP cards.

- MLB: Red Sox YouTube channel RSS (no auth)
- NHL: NHL's public score endpoint exposes recap/condensed game URLs
       which point to Brightcove videos (no auth)
"""

import re
import requests
import xml.etree.ElementTree as ET
from datetime import date

RED_SOX_CHANNEL = "UCoLrny_Oky6BE206kOfTmiw"
NHL_BRIGHTCOVE_ACCOUNT = "6415718365001"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def find_red_sox_recap(game_date: date) -> str | None:
    """Find the official Red Sox channel recap for a given game date.

    Red Sox post videos with titles like:
      'Red Sox vs. Orioles Game Highlights (4/25/26) | MLB Highlights'
      'FULL HIGHLIGHTS: Red Sox Beat Tigers on the Best Day in Boston (4/20/26)'

    Returns the YouTube video URL (https://www.youtube.com/watch?v=...) or
    None if not found in the last 15 videos.
    """
    try:
        resp = requests.get(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={RED_SOX_CHANNEL}",
            timeout=10,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError):
        return None

    # Build the date strings we expect to see in titles: "(4/25/26)"
    short_year = game_date.strftime("%y")
    date_patterns = [
        f"({game_date.month}/{game_date.day}/{short_year})",
        f"{game_date.month}/{game_date.day}/{short_year}",
    ]

    for entry in root.findall("atom:entry", NS):
        title_el = entry.find("atom:title", NS)
        vid_el = entry.find("yt:videoId", NS)
        if title_el is None or vid_el is None:
            continue
        title = title_el.text or ""
        title_lower = title.lower()

        # Must be a recap/highlights video
        if "highlight" not in title_lower:
            continue
        # Must contain the game date
        if not any(p in title for p in date_patterns):
            continue

        return f"https://www.youtube.com/watch?v={vid_el.text}"

    return None


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
