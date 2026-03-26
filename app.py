"""Watch or Skip? — Should Matt watch the game he missed?"""

import streamlit as st
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Watch or Skip? — Matt Gaines' Decision Maker",
    page_icon="🎮",
    layout="centered",
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Cards ──────────────────────────────────────────── */
    .verdict-yes {
        background: linear-gradient(135deg, #1a5c1a, #2d8a2d);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-left: 5px solid #4CAF50;
    }
    .verdict-no {
        background: linear-gradient(135deg, #5c1a1a, #8a2d2d);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-left: 5px solid #f44336;
    }
    .verdict-home {
        background: linear-gradient(135deg, #1a3d5c, #2d5a8a);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-left: 5px solid #2196F3;
    }
    .verdict-upcoming {
        background: linear-gradient(135deg, #2a2a2a, #3a3a3a);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-left: 5px solid #888;
    }
    .verdict-warn {
        background: linear-gradient(135deg, #5c4a1a, #8a6d2d);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-left: 5px solid #ff9800;
    }
    .big-verdict {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.25rem;
    }
    .reason-text {
        font-size: 1.05rem;
        font-weight: 600;
        opacity: 0.95;
    }
    .score-text {
        font-size: 0.95rem;
        opacity: 0.8;
        margin-top: 0.25rem;
    }
    .card-header {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }
    .card-header img {
        height: 32px;
        vertical-align: middle;
        margin-right: 6px;
    }
    .summary-banner {
        text-align: center;
        padding: 0.75rem;
        border-radius: 8px;
        background: #141830;
        margin-bottom: 1rem;
        font-size: 1.05rem;
    }

    /* ── Force date picker row to stay inline ────────── */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }

    /* ── Mobile overrides ────────────────────────────── */
    @media (max-width: 640px) {
        .stMainBlockContainer {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }

        /* Cards */
        .verdict-yes, .verdict-no, .verdict-home,
        .verdict-upcoming, .verdict-warn {
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 8px;
        }
        .big-verdict {
            font-size: 1.4rem;
        }
        .card-header {
            font-size: 0.9rem;
            line-height: 1.3;
        }
        .card-header img {
            height: 22px;
            margin-right: 4px;
        }
        .reason-text {
            font-size: 0.85rem;
        }
        .score-text {
            font-size: 0.8rem;
        }
        .summary-banner {
            font-size: 0.85rem;
            padding: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# ── Cached data fetchers ────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_mlb(date_str: str):
    try:
        from data.mlb_client import get_games_for_date
        return get_games_for_date(date_str), None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nhl(date_str: str):
    try:
        from data.nhl_client import get_games_for_date
        return get_games_for_date(date_str), None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ncaa(date_str: str):
    try:
        from data.ncaa_client import get_games_for_date
        return get_games_for_date(date_str), None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_mlb_upcoming():
    try:
        from data.mlb_client import get_upcoming_games
        return get_upcoming_games(days=7), None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nhl_upcoming():
    try:
        from data.nhl_client import get_upcoming_games
        return get_upcoming_games(days=7), None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ncaa_upcoming():
    try:
        from data.ncaa_client import get_upcoming_games
        return get_upcoming_games(days=7), None
    except Exception as e:
        return [], str(e)


# ── Card rendering ──────────────────────────────────────────────────────

SPORT_LOGO = {
    "mlb": "https://a.espncdn.com/i/teamlogos/mlb/500/bos.png",
    "nhl": "https://a.espncdn.com/i/teamlogos/nhl/500/wsh.png",
    "ncaa": "https://a.espncdn.com/i/teamlogos/ncaa/500/2244.png",
}

SPORT_EMOJI = {
    "mlb": "⚾",
    "nhl": "🏒",
    "ncaa": "🏀",
}


def _logo_img(sport: str) -> str:
    """Return an inline HTML img tag for the sport's team logo."""
    url = SPORT_LOGO.get(sport, "")
    if url:
        return f'<img src="{url}">'
    return SPORT_EMOJI.get(sport, "🏅") + " "

SPORT_TEAM = {
    "mlb": "Red Sox",
    "nhl": "Capitals",
    "ncaa": "GMU",
}


def _build_score_str(sport: str, game: dict) -> str:
    """Build a final score string for display on NO cards only."""
    if sport == "mlb" and "final_score" in game:
        fs = game["final_score"]
        extra = f" ({game['innings_played']})" if game.get("went_extra_innings") else ""
        return f"{fs['away_runs']} – {fs['home_runs']}{extra}"
    elif sport == "nhl":
        caps_g = game.get("caps_goals", "?")
        opp_g = game.get("opponent_goals", "?")
        suffix = ""
        if game.get("went_to_shootout"):
            suffix = " (SO)"
        elif game.get("went_to_ot"):
            suffix = " (OT)"
        if game.get("caps_home"):
            return f"{opp_g} – {caps_g}{suffix}"
        else:
            return f"{caps_g} – {opp_g}{suffix}"
    elif sport == "ncaa":
        gmu_p = game.get("gmu_points", "?")
        opp_p = game.get("opponent_points", "?")
        if game.get("was_home_game"):
            return f"{opp_p} – {gmu_p}"
        else:
            return f"{gmu_p} – {opp_p}"
    return ""


def render_verdict_card(sport: str, game: dict, verdict: str, reason: str):
    """Render a WATCH/SKIP/HOME verdict card."""
    logo = _logo_img(sport)

    away = game.get("away_team", "?")
    home = game.get("home_team", "?")
    matchup = f"{away} @ {home}"

    # Map internal verdict to display label
    if verdict == "YES":
        display = "WATCH"
        icon = "✅"
        css_class = "verdict-yes"
    elif verdict == "NO":
        display = "SKIP"
        icon = "❌"
        css_class = "verdict-no"
    elif verdict == "HOME":
        display = "HOME"
        icon = "🏠"
        css_class = "verdict-home"
    else:
        display = verdict
        icon = "⚠️"
        css_class = "verdict-warn"

    # WATCH: logo + matchup + badge only (zero spoilers)
    # SKIP: badge + reason + final score
    # HOME: logo + matchup + badge only
    extra_lines = ""
    if verdict == "NO":
        extra_lines = f'<div class="reason-text">{reason}</div>'
        score_str = _build_score_str(sport, game)
        if score_str:
            extra_lines += f'\n        <div class="score-text">Final: {score_str}</div>'

    st.markdown(f"""
    <div class="{css_class}">
        <div class="card-header">{logo}{matchup}</div>
        <div class="big-verdict">{icon} {display}</div>
        {extra_lines}
    </div>
    """, unsafe_allow_html=True)


def render_no_game_card(sport: str, message: str = "No game on this date"):
    logo = _logo_img(sport)
    team = SPORT_TEAM.get(sport, "")
    st.markdown(f"""
    <div class="verdict-upcoming">
        <div class="card-header">{logo}{team} — {message}</div>
    </div>
    """, unsafe_allow_html=True)


def render_status_card(sport: str, game: dict):
    """Render a postponed/upcoming/etc card."""
    logo = _logo_img(sport)
    team = SPORT_TEAM.get(sport, "")
    status = game.get("status", "Unknown")
    away = game.get("away_team", "?")
    home = game.get("home_team", "?")
    matchup = f"{away} @ {home}"

    if status == "Upcoming":
        css_class = "verdict-upcoming"
        icon = "🕐"
        label = "Game not yet played"
        time_str = game.get("start_time_utc", "")
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                et_start = dt.astimezone(EASTERN)
                now_et = datetime.now(EASTERN)
                duration = {"mlb": 3, "nhl": 2.5, "ncaa": 2}.get(sport, 2.5)
                et_end = et_start + timedelta(hours=duration)
                start_str = _eastern_str(et_start)
                end_str = _eastern_str(et_end)

                if now_et < et_start:
                    label = f"Starts at {start_str}"
                elif now_et < et_end:
                    icon = "⏳"
                    label = f"Started at {start_str} · Likely in progress · Check back after ~{end_str}"
                else:
                    icon = "🔄"
                    label = f"Started at {start_str} · Should be final soon · Hit 🔄 to refresh"
            except (ValueError, TypeError):
                pass
    elif status == "Postponed":
        css_class = "verdict-warn"
        icon = "⚠️"
        label = "Postponed"
    else:
        css_class = "verdict-upcoming"
        icon = "ℹ️"
        label = status

    st.markdown(f"""
    <div class="{css_class}">
        <div class="card-header">{logo}{matchup}</div>
        <div class="big-verdict">{icon}</div>
        <div class="reason-text">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_upcoming_card(game: dict):
    """Render a card for the schedule view."""
    sport = game.get("sport", "")
    logo = _logo_img(sport)
    team = SPORT_TEAM.get(sport, "")
    away = game.get("away_team", "?")
    home = game.get("home_team", "?")
    matchup = f"{away} @ {home}"

    time_str = game.get("date", "")
    display_date = ""
    if time_str:
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            display_date = dt.astimezone(EASTERN).strftime("%a %b %d · ") + _eastern_str(dt)
        except (ValueError, TypeError):
            display_date = time_str[:10] if len(time_str) >= 10 else time_str

    status = game.get("status", "")
    if status in ("Final", "OFF"):
        label = "Final"
        css_class = "verdict-upcoming"
    else:
        label = "Upcoming"
        css_class = "verdict-upcoming"

    st.markdown(f"""
    <div class="{css_class}">
        <div class="card-header">{logo}{matchup}</div>
        <div class="score-text">🕐 {display_date}</div>
        <div class="reason-text">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Eastern time (auto-handles EST/EDT) ──────────────────────────────────

EASTERN = ZoneInfo("America/New_York")


def _eastern_str(dt_aware) -> str:
    """Format an aware datetime as '04:10 PM EDT' / '04:10 PM EST'."""
    et = dt_aware.astimezone(EASTERN)
    suffix = et.strftime("%Z")  # EDT or EST
    return et.strftime(f"%I:%M %p {suffix}")


# ── Date picker ──────────────────────────────────────────────────────────

def render_date_picker():
    """Date picker: prev/next buttons with date input, all in one row."""
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    # Row 1: ◀  date input  ▶  🔄  — use small fixed-width columns
    c1, c2, c3, c4 = st.columns([1, 4, 1, 1], gap="small")

    with c1:
        if st.button("◀", key="prev_day", use_container_width=True):
            st.session_state.selected_date -= timedelta(days=1)
            st.rerun()

    with c2:
        picked = st.date_input(
            "date_picker",
            value=st.session_state.selected_date,
            label_visibility="collapsed",
        )
        if picked != st.session_state.selected_date:
            st.session_state.selected_date = picked
            st.rerun()

    with c3:
        if st.button("▶", key="next_day", use_container_width=True):
            st.session_state.selected_date += timedelta(days=1)
            st.rerun()

    with c4:
        if st.button("🔄", key="refresh", use_container_width=True, help="Refresh"):
            fetch_mlb.clear()
            fetch_nhl.clear()
            fetch_ncaa.clear()
            st.rerun()

    return st.session_state.selected_date


# ── Main App ────────────────────────────────────────────────────────────

st.title("Watch or Skip?")
st.caption("Matt Gaines' Decision Maker")

check_date = render_date_picker()
st.markdown(f"**{check_date.strftime('%A, %B %d, %Y')}**")
date_str = check_date.strftime("%Y-%m-%d")

# ── Lock & load: show a full-width status bar while fetching ─────────

results_container = st.container()
loading_placeholder = st.empty()
loading_placeholder.markdown(
    '<div class="summary-banner">Loading games...</div>',
    unsafe_allow_html=True,
)

mlb_games, mlb_err = fetch_mlb(date_str)
nhl_games, nhl_err = fetch_nhl(date_str)
ncaa_games, ncaa_err = fetch_ncaa(date_str)

loading_placeholder.empty()

# ── Build cards ──────────────────────────────────────────────────────────

total_games = 0
worth_watching = 0
cards = []

# MLB
if mlb_err:
    cards.append(("mlb", {"status": "error", "msg": mlb_err}, None, None))
elif not mlb_games:
    cards.append(("mlb", None, None, None))
else:
    from rules.mlb import evaluate as mlb_eval
    for g in mlb_games:
        if g.get("status") == "Final":
            total_games += 1
            v, r = mlb_eval(g)
            if v == "YES":
                worth_watching += 1
            cards.append(("mlb", g, v, r))
        else:
            cards.append(("mlb", g, None, None))

# NHL
if nhl_err:
    cards.append(("nhl", {"status": "error", "msg": nhl_err}, None, None))
elif not nhl_games:
    cards.append(("nhl", None, None, None))
else:
    from rules.nhl import evaluate as nhl_eval
    for g in nhl_games:
        if g.get("status") == "Final":
            total_games += 1
            v, r = nhl_eval(g)
            if v == "YES":
                worth_watching += 1
            cards.append(("nhl", g, v, r))
        else:
            cards.append(("nhl", g, None, None))

# NCAA
if ncaa_err:
    cards.append(("ncaa", {"status": "error", "msg": ncaa_err}, None, None))
elif not ncaa_games:
    cards.append(("ncaa", None, None, None))
else:
    from rules.ncaa import evaluate as ncaa_eval
    for g in ncaa_games:
        if g.get("status") == "Final":
            total_games += 1
            v, r = ncaa_eval(g)
            if v in ("YES", "HOME"):
                worth_watching += 1
            cards.append(("ncaa", g, v, r))
        else:
            cards.append(("ncaa", g, None, None))

# ── Summary banner ──
has_upcoming = any(g and g.get("status") == "Upcoming" for _, g, _, _ in cards)
if total_games > 0:
    msg = f'{worth_watching} of {total_games} game{"s" if total_games != 1 else ""} worth watching'
elif has_upcoming:
    upcoming_count = sum(1 for _, g, _, _ in cards if g and g.get("status") == "Upcoming")
    msg = f'{upcoming_count} game{"s" if upcoming_count != 1 else ""} scheduled · not yet played'
else:
    msg = "No games on this date"

with results_container:
    st.markdown(f'<div class="summary-banner">{msg}</div>', unsafe_allow_html=True)

# ── Render cards ──
for sport, game, verdict, reason in cards:
    with results_container:
        if game is None:
            render_no_game_card(sport)
        elif game.get("status") == "error":
            st.warning(f"{SPORT_EMOJI.get(sport, '')} {SPORT_TEAM.get(sport, '')} error: {game['msg']}")
        elif verdict is not None:
            render_verdict_card(sport, game, verdict, reason)
        else:
            render_status_card(sport, game)
