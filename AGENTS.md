# Watch Or Skip Guide

Streamlit app that applies deterministic sports rules to decide whether completed games are worth watching.

## Run

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Key Files

- `app.py`: Streamlit interface.
- `rules/mlb.py`: Red Sox rules.
- `rules/nhl.py`: Capitals rules.
- `rules/ncaa.py`: George Mason basketball rules.
- `data/*_client.py`: external data clients.

## Conventions

- Keep verdicts deterministic and rule-based.
- Do not add LLM calls to verdict generation.
- Preserve spoiler-aware UI behavior.
- Prefer tests or small direct rule checks when changing rules.
