# NEUROCITY

NEUROCITY is a local-first simulation platform for observing a near-future autonomous city populated by AI-driven citizens. It is built as a deterministic systems simulator with a FastAPI backend, SQLite persistence, WebSocket tick streaming, and a dense live dashboard.

## What It Simulates

- 5,000+ vectorized citizens with jobs, home districts, wealth, stress, ideology, health, memories, and meme exposure
- District-level housing, transport, crime, pollution, energy demand, transit quality, wealth, and political leaning
- Companies that expand, contract, hire, fire, lobby, and fail under economic pressure
- Government approval, taxation, infrastructure budget, policing, surveillance, corruption, protests, and election drift
- Meme propagation, outrage cycles, polarization, mutation, social fatigue, and cultural trends
- Emergent events caused by thresholds in the real simulation state, not scripted story beats

## Architecture

```text
neurocity/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── seed.py
│   ├── api/routes.py
│   ├── websocket/routes.py
│   ├── simulation/
│   │   ├── engine.py
│   │   ├── tick_manager.py
│   │   ├── world_state.py
│   │   ├── event_system.py
│   │   ├── scheduler.py
│   │   ├── agents/
│   │   ├── systems/
│   │   ├── ai/
│   │   └── procedural/
│   ├── templates/dashboard.html
│   └── static/
│       ├── css/dashboard.css
│       ├── js/dashboard.js
│       └── vendor/
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## Simulation Loop

The engine advances in deterministic ticks. Each tick runs the system pipeline:

1. Transportation updates commute pressure, congestion, citizen stress, and productivity.
2. Employment updates hiring, layoffs, wages, job seeking, and unemployment.
3. Housing updates rent, migration pressure, happiness, and wealth drift.
4. Energy and climate update blackouts, pollution, health, stress, and infrastructure quality.
5. Crime updates district risk from poverty, unemployment, policing, inequality, and corruption.
6. Social network and culture update meme spread, ideology, polarization, happiness, and social fatigue.
7. Economy updates company growth, failures, GDP, inflation, business activity, and tech evolution.
8. Politics updates approval, protests, policy pressure, taxes, policing, surveillance, and elections.
9. Event generation emits observable crises only when state thresholds are crossed.
10. Newspaper generation summarizes actual simulation state.

The random source is derived from `seed + tick + system salt`, so save/load replay remains deterministic.

## API

- `GET /dashboard`
- `GET /city`
- `GET /districts`
- `GET /citizens`
- `GET /economy`
- `GET /events`
- `GET /interventions`
- `POST /simulation/start`
- `POST /simulation/pause`
- `POST /simulation/reset`
- `POST /simulation/speed`
- `POST /simulation/tick`
- `POST /intervention`
- `POST /policy`
- `POST /save`
- `POST /load`
- `WS /ws/simulation`

## Configuration And Secrets

Runtime configuration is loaded from `.env` with the `NEUROCITY_` prefix. The local `.env` file is ignored by git; commit `.env.example` only.

Use `.env` or deployment environment variables for values that may become sensitive, especially database URLs with credentials, remote Ollama endpoints, future API tokens, and production feature flags.

Key settings:

- `NEUROCITY_DATABASE_URL` controls the SQLAlchemy database connection.
- `NEUROCITY_DEFAULT_SEED`, `NEUROCITY_DEFAULT_POPULATION`, and `NEUROCITY_DEFAULT_DISTRICTS` control the initial world.
- `NEUROCITY_ENABLE_LLM`, `NEUROCITY_OLLAMA_URL`, and `NEUROCITY_OLLAMA_MODEL` control the optional local LLM layer.

## Startup

```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/dashboard`.

## Tests

```bash
uv run pytest
```

The test suite covers deterministic ticks, save/load replay, economy and citizen behavior, event generation, API endpoints, WebSocket updates, and a 5,000-citizen performance constraint.

## Optional Ollama Layer

The core simulator never depends on an LLM. `app/simulation/ai/llm_events.py` provides a best-effort local Ollama helper for future newspaper or citizen conversation flavor. Enable it in `.env` with `NEUROCITY_ENABLE_LLM=true`, `NEUROCITY_OLLAMA_URL`, and `NEUROCITY_OLLAMA_MODEL`.

## 👤 Author

**Slava Serdiukov**
Machine Learning / Backend Engineering Portfolio Project
