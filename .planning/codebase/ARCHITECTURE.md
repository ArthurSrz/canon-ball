# Architecture

**Analysis Date:** 2026-06-08

## Pattern Overview

**Overall:** Client-server REST architecture with experimental backend and React frontend. Chain-centric measurement system where the Borges attribution graph is the central artifact explaining semantic dispersion results.

**Key Characteristics:**
- Dual instrument design: Canon Ball measures semantic precision (output WHAT), Borges Graph explains causal attribution (WHY)
- Backend drives experiment execution (trials, embeddings, analysis) asynchronously; frontend is visualization layer
- Backend serves pre-built React SPA at root; frontend calls backend via `/api/*` routes
- Chain computation happens in background thread after UMAP analysis completes (synchronization via threading lock)
- Feature identifiers preserved throughout for future steering interventions

## Layers

**FastAPI Backend:**
- Purpose: Manages experiment execution, UMAP projection, statistical analysis, and attribution chain building
- Location: `backend/`
- Contains: REST routers, Pydantic schemas, configuration
- Depends on: `canon_experiment.py`, `canon_analysis.py`, `borges_graph.py`, `neuronpedia_client.py`
- Used by: React frontend via `/api/experiment` and `/api/chain` routes

**Experiment Engine (Synchronous CPU/Memory Intensive):**
- Purpose: Runs N trials with and without knowledge layer, generates model outputs, embeds via fastembed
- Location: `canon_experiment.py`
- Contains: Trial generation, backend detection (ollama vs OpenRouter), embedding computation
- Depends on: OpenRouter API (gemma-3-4b-it), fastembed (BAAI/bge-small-en-v1.5)
- Used by: `backend/routers/experiment.py` via `run_experiment()` and `load_experiment()`

**Analysis Engine (UMAP + Statistics):**
- Purpose: Computes semantic space projections, dispersion metrics (euclidean/cosine), Mann-Whitney U test
- Location: `canon_analysis.py`
- Contains: UMAP dimensionality reduction, centroid computation, pairwise distance analysis
- Depends on: scikit-learn (cosine_distances), scipy (mannwhitneyu), umap-learn
- Used by: `backend/routers/experiment.py` via `full_analysis()`

**Attribution Graph Builder (Autoregressive Tracing):**
- Purpose: Traces token-by-token generation with Circuit Tracer API to build causal chain
- Location: `borges_graph.py`
- Contains: `CompiledGraph` and `Step` dataclasses, Neuronpedia integration
- Depends on: `neuronpedia_client.py` for Circuit Tracer calls
- Used by: `backend/routers/chain.py` via `compile_attribution()`

**Neuronpedia Client (External API Integration):**
- Purpose: Wraps Neuronpedia NLA (Natural Language Autoencoder) for circuit tracing and activation verbalization
- Location: `neuronpedia_client.py`
- Contains: API calls for attribution graphs, feature verbalization, batching logic (16-position cap)
- Depends on: Neuronpedia API (gemma-2-2b for Circuit Tracer, gemma-3-27b-it for NLA)
- Used by: `borges_graph.py` and `backend/routers/chain.py`

**React Frontend (SPA):**
- Purpose: Visualization and control interface with 6-step rail navigation, tweaks panel
- Location: `frontend/src/`
- Contains: Screens (Concept, Setup, Map, Metrics, Modes, Focal Line), components (CannonScene, SemanticMap, TweaksPanel), hooks
- Depends on: React 18.3, Vite 6.0, backend API
- Used by: User navigates through steps, fires experiments, views results

**Configuration Management:**
- Purpose: Unified environment variable loading (replaces Streamlit st.secrets)
- Location: `backend/config.py`
- Contains: `.env` parsing, API key getters
- Depends on: None (pure stdlib)
- Used by: Backend routers and libraries to resolve OpenRouter and Neuronpedia keys

## Data Flow

**Experiment Firing Flow:**

1. User enters prompt + knowledge layer in `SetupScreen`, clicks "Load the Canon"
2. Frontend calls `POST /api/experiment/fire` with `FireRequest`
3. Backend routes to `_run_experiment_sync`:
   - Calls `canon_experiment.run_experiment()` to generate N control + N test trials
   - Saves raw experiment data to `results/experiment.json`
   - Acquires `_umap_lock` and calls `canon_analysis.full_analysis()` for UMAP projection
   - Saves analysis to `results/analysis.json`
   - Returns normalized projection + metrics to frontend immediately
   - Launches `start_chains_bg()` in background thread to build Borges chains
4. Frontend displays `MapScreen` showing semantic landing zones (UMAP projection)
5. Meanwhile, background thread computes two attribution chains (control + test) and writes to `results/chain_control.json`, `results/chain_test.json`
6. When user navigates to `MetricsScreen` or `FocalLineScreen`, frontend polls `/api/chain/status` until chains are ready

**Chain Building Flow:**

1. `start_chains_bg()` runs in daemon thread after experiment completes
2. For each chain (control, test):
   - Calls `borges_graph.compile_attribution()` with prompt ± knowledge layer
   - For each token position, calls Neuronpedia `generate_attribution_graph()` to get Circuit Tracer subgraph
   - Extracts predicted token (top logit) and stores both in `Step` object
   - Calls callback `on_step()` to update chain status
   - Saves full `CompiledGraph.to_dict()` to disk
3. Thread sets `_chain_state` to "ready" on success or "failed" on error

**Focal Line Scene Building Flow:**

1. User on `FocalLineScreen` clicks "Build the focal line" or auto-triggers on screen load
2. Frontend calls `POST /api/chain/focal` with `FocalRequest`
3. Backend:
   - Calls `neuronpedia_client.generate_attribution_graph()` for Circuit Tracer subgraph
   - Fetches pruned subgraph (max 40 nodes, 200 links) via `fetch_attribution_subgraph()`
   - Calls `neuronpedia_client.verbalize_activations()` for NLA token explanations (gemma-3-27b-it, layer 41)
   - Builds scene object: `{inputs, converge, focus, answer, diverge}` via `_build_focal_scene()`
   - Returns scene shape expected by `FocalLineScreen`

**State Management:**

- Frontend: React hooks (`useExperiment`, `useTweaks`) hold experiment results and UI tweaks in component state
- Backend: Results written to disk (`results/`) to survive server restarts; chains built in background thread with lock-protected state dict
- UMAP computation serialized with `_umap_lock` (Numba not thread-safe)

## Key Abstractions

**Experiment Result:**
- Purpose: Holds N control trials and N test trials with embeddings
- Examples: `canon_experiment.run_experiment()` returns `ExperimentData` namedtuple
- Pattern: Trials are serialized to `results/experiment.json` and reloaded by analysis and API endpoints

**Dispersion Metrics:**
- Purpose: Quantifies "landing zone" tightness (coherence of semantic outputs)
- Examples: `canon_analysis.compute_dispersion()` returns euclidean/cosine distances to centroid
- Pattern: Control vs test dispersion ratio is the primary WHAT measurement (tightening %)

**Injection Modes:**
- Purpose: Experimental variable controlling how knowledge layer is introduced into model
- Examples: `system_user`, `interleave`, `template`, `cot_priming` (defined in `canon_experiment.INJECTION_MODES`)
- Pattern: Each mode is a different prompt engineering strategy; `FireRequest.injection_mode` selects which to run

**CompiledGraph:**
- Purpose: Autoregressive chain of attribution steps, preserving feature IDs for steering
- Examples: `borges_graph.CompiledGraph` holds list of `Step` objects
- Pattern: Each step has token, context_length, and optional subgraph; `all_feature_ids()` extracts SAE indices for future interventions

**Focal Line Scene:**
- Purpose: Maps Circuit Tracer subgraph + NLA verbalizations into left-middle-right visualization
- Examples: `{inputs, converge, focus, answer, diverge}` objects
- Pattern: Inputs = prompt tokens, converge = top features (colored by knowledge influence), focus = predicted token, diverge = NLA descriptions

## Entry Points

**Backend Startup:**
- Location: `backend/main.py`
- Triggers: `python3 -m uvicorn backend.main:app --port 8000 --reload`
- Responsibilities: CORS setup, router mounting, warmup (fastembed pre-load), SPA serving

**Experiment POST:**
- Location: `backend/routers/experiment.py:fire_experiment()`
- Triggers: Frontend `POST /api/experiment/fire`
- Responsibilities: Run trials, analyze, save to disk, kick off background chain building, return immediate response

**Chain Results Polling:**
- Location: `backend/routers/chain.py:get_chain_status()`
- Triggers: Frontend `GET /api/chain/status` (poll loop in `useExperiment` hook)
- Responsibilities: Return thread-safe chain computation state (idle/computing/ready/failed)

**React Mount:**
- Location: `frontend/src/main.jsx` → `App.jsx`
- Triggers: Browser loads `http://localhost:5173` (dev) or production root
- Responsibilities: Initialize step navigation, mock data, tweak state; render 6-step rail

## Error Handling

**Strategy:** Graceful degradation with fallback paths

**Patterns:**

- **Missing Experiment Results:** `GET /api/experiment/results` returns 404 if `experiment.json` not found; frontend shows placeholder mock data
- **Chain Computation Failure:** Background thread catches exception, sets `_chain_state["error"]` and `state="failed"`; frontend displays error message instead of scene
- **API Key Missing:** Health endpoint checks both keys; if missing, experiment will fail with runtime error
- **UMAP Lock Timeout:** Not explicitly handled; would block forever if thread holding lock crashes (known limitation)
- **NLA Timeout:** 90-second timeout on Neuronpedia requests; if exceeded, scene uses placeholder node
- **Incomplete Subgraph:** If Circuit Tracer returns no feature nodes, scene shows "(attribution unavailable)" placeholder

## Cross-Cutting Concerns

**Logging:** `print(..., flush=True)` to stdout for async operations; no structured logging framework

**Validation:** Pydantic models (`FireRequest`, `TraceRequest`, `FocalRequest`) validate request shapes; no runtime type checking on results

**Authentication:** Optional API keys (OpenRouter, Neuronpedia); code detects and gracefully handles missing keys with runtime errors

**Rate Limiting:** Circuit Tracer has 30/hr limit (documented in `borges_graph.py`); NLA explain caps at 16 new token positions per request (auto-batched by client)

**Thread Safety:** UMAP calls protected by `_umap_lock`; chain computation runs in daemon thread without explicit state machine (relies on flag updates)

---

*Architecture analysis: 2026-06-08*
