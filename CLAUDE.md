# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Canon Ball is a chain-centric interpretability instrument that measures what knowledge layers do to LLMs. Two instruments work as one:

1. **Canon Ball** — fires N trials with and without a knowledge layer, embeds outputs, compares semantic "landing zones" (dispersion, centroid shift, Mann-Whitney U). Measures the **WHAT**.
2. **Borges Graph / Focal Line** — traces the attribution chain (Circuit Tracer) and NLA verbalizations to explain **WHY** dispersion reduces. The chain is the central artifact.

## Running

```bash
# Backend (FastAPI)
python3 -m uvicorn backend.main:app --port 8000 --reload

# Frontend (React/Vite)
cd frontend && npm run dev
```

Set API keys in `.env` (see `.env.example`):
- `OPENROUTER_API_KEY` — required for trial generation (gemma-3-4b-it)
- `NEURONPEDIA_API_KEY` — optional, raises rate limits for Circuit Tracer

## Architecture

### Backend (FastAPI)
- **`backend/main.py`** — FastAPI app, CORS, router mounting.
- **`backend/config.py`** — Unified config from `.env` (replaces old st.secrets).
- **`backend/routers/experiment.py`** — `POST /api/experiment/fire`, `GET /api/experiment/results`.
- **`backend/routers/chain.py`** — `POST /api/chain/trace`, `POST /api/chain/focal` (builds focal line scene from Circuit Tracer + NLA).
- **`backend/schemas.py`** — Pydantic request models.

### Frontend (React/Vite)
- **`frontend/src/App.jsx`** — Shell with 6-step rail navigation + tweaks panel.
- **`frontend/src/screens/`** — ConceptScreen, SetupScreen, MapScreen, MetricsScreen, ModesScreen, FocalLineScreen.
- **`frontend/src/components/`** — CannonScene (hero animation), SemanticMap (UMAP viz), FocalLine (SVG), TweaksPanel.
- **`frontend/src/styles.css`** — RawBlock brutalist design system.
- **`frontend/src/mockData.js`** — Fallback mock data matching real API response shape.

### Libraries (no framework dependency)
- **`borges_graph.py`** — Compiled attribution graph builder. `compile_attribution(prompt, system_prompt, max_tokens)` → `CompiledGraph`. Preserves SAE feature identifiers for future steering.
- **`canon_experiment.py`** — Experiment engine. Four injection modes (`system_user`, `interleave`, `template`, `cot_priming`). Uses gemma-3-4b-it via OpenRouter + fastembed for embeddings.
- **`canon_analysis.py`** — UMAP projection, dispersion metrics, Mann-Whitney U.
- **`neuronpedia_client.py`** — NLA + Circuit Tracer client. Batched explain (16 positions/request cap), attribution graph generation + pruning.

### Legacy (Streamlit — still present, will be removed)
- `app.py`, `pages/`, `shared_sidebar.py`, `html_components.py`

## Key design details

- **Chain-centric**: The Borges chain is THE central artifact. Dispersion measures the WHAT, chain shows the WHY.
- **Two chains per experiment**: 1 control + 1 with KL (not per-trial — rate limits).
- **Models**: gemma-3-4b-it (OpenRouter) for trials, gemma-2-2b (Neuronpedia Circuit Tracer) for attribution, gemma-3-27b-it (NLA layer 41) for verbalization.
- **Design**: RawBlock brutalist — white ground, black borders, control=black, test=red, knowledge=orange.
- Injection modes are the core experimental variable.
- NLA explain endpoint caps at 16 new token positions per request; the client batches automatically.
- Circuit Tracer: gemma-2-2b only, 64-token prompt cap. Sliding window when context exceeds cap.
- `fetch_attribution_subgraph` preserves the `feature` field (SAE dictionary index) for future steering.
