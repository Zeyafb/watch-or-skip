# Watch or Skip? 🎮

A Streamlit app that tells you whether a completed sports game was worth watching, based on custom rules — no AI, no guessing, just deterministic logic on real sports data.

## Teams Tracked

- ⚾ **Boston Red Sox** (MLB) — via MLB Stats API
- 🏒 **Washington Capitals** (NHL) — via NHL API
- 🏀 **George Mason Patriots** (NCAA Basketball) — via ESPN API

## How It Works

Each sport has a rules engine that evaluates completed games:

**MLB (Red Sox):**
1. Shutout (0 runs) → Skip
2. Red Sox won → Watch
3. Extra innings → Watch
4. Close entering bottom 9th (Sox home) → Watch
5. Tying run at the plate in 9th+ → Watch
6. Otherwise → Skip

**NHL (Capitals):**
1. OT or Shootout → Watch
2. Caps won → Watch
3. Shutout loss → Skip
4. One-goal loss (excluding empty netters) → Watch
5. Otherwise → Skip

**NCAA (GMU):**
- Home games → Auto watch (Matt watches these live)
- Away win → Watch
- Away loss → Skip

## Two Modes

- **What did I miss?** — Pick a date, see verdicts for all games that day
- **What's on?** — 7-day lookahead across all three teams

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Hosting

Deployed on [Streamlit Community Cloud](https://streamlit.io/cloud), connected to this GitHub repo. Pushes to `main` auto-deploy.

## Cost

Zero. All APIs are free. No LLM calls. No tokens. No subscriptions.
