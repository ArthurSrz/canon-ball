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

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Canon Ball**

An interpretability instrument for researchers studying what knowledge does to language models. Researchers configure a prompt and a knowledge layer (system prompt), fire paired experiments (control: LLM without knowledge / test: LLM with knowledge), and read two complementary answers: Canon Ball's semantic dispersion metrics (the WHAT) and a differential Borges graph comparing attribution chains (the WHY — which tokens the knowledge activated).

**Core Value:** A researcher can fire one experiment and get a direct, visual answer to "what did this knowledge layer do to this model's output distribution?"

### Constraints

- **Tech stack**: FastAPI + React/Vite — no switching mid-flight
- **Models**: gemma-3-4b-it (OpenRouter) for trials; gemma-2-2b (Neuronpedia) for attribution — API-locked
- **Rate limits**: Circuit Tracer 30/hr hard cap; NLA 16-position batch cap
- **Knowledge form**: System prompt layer only (not RAG, not fine-tuning)
- **Scope**: Configure + fire + read results in a single session (no persistence)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.13 - Backend, experiment engine, analysis, and library code
- JavaScript (ES6+/TypeScript-ready) - Frontend React components and application logic
- CSS3 - RawBlock brutalist design system in `frontend/src/styles.css`
- JSON - Configuration and data interchange
## Runtime
- Python 3.13 (specified by CICD/Nix, see `nixpacks.toml`)
- Node.js 20 (for frontend build, specified in `nixpacks.toml`)
- Python: `pip` with `requirements.txt`
- Node.js: `npm` with `package-lock.json`
- Lockfile: Both present and committed
## Frameworks
- FastAPI 0.115.0+ - REST API framework, CORS middleware, request/response handling
- Uvicorn 0.32.0+ - ASGI server for FastAPI
- React 18.3.1 - UI framework
- Vite 6.0.0 - Build tool and dev server with proxy support for API calls
- None configured (no test framework found in dependencies)
- Vite with `@vitejs/plugin-react` 4.3.0 - React fast refresh and bundling
- TypeScript types available: `@types/react`, `@types/react-dom` (dev dependencies)
## Key Dependencies
- `numpy` - Numerical arrays for embedding operations and UMAP projection
- `scikit-learn` - UMAP dimensionality reduction, Mann-Whitney U statistical tests
- `scipy` - Statistical functions (Mann-Whitney U)
- `umap-learn` - Dimensionality reduction for semantic projection visualization
- `fastembed` (BAAI/bge-small-en-v1.5 model) - Local embedding model for cloud backend
- `requests` - HTTP client for OpenRouter, Hugging Face, Neuronpedia, Ollama APIs
- `fastapi` - HTTP server with automatic JSON serialization, CORS, type validation
- `pydantic` - Request/response validation with camelCase alias support
- `uvicorn` - ASGI application server with reload and host binding support
## Configuration
- `.env` file (not committed, see `.env.example`)
- Environment variables read in `backend/config.py` without external dependencies
- Supports manual or automatic detection of backend (ollama vs. cloud)
- Override via `CANON_BACKEND` env var: "cloud" or "ollama" (default: auto-detect)
- `backend/config.py` - Centralized config for API keys (OpenRouter, Neuronpedia, HuggingFace)
- `requirements.txt` - Python dependencies (pinned to minimum versions, not locked)
- `frontend/package.json` - Node dependencies with caret ranges (allow patch/minor updates)
- `frontend/vite.config.js` - Vite dev server with API proxy to `http://localhost:8000`
- `nixpacks.toml` - CICD build configuration for Nixpacks deployment
- `Procfile` - Heroku/Procfile-compatible deployment: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
## Platform Requirements
- Python 3.13 with pip
- Node.js 20 with npm
- Local Ollama installation optional (auto-detected for local embedding/chat)
- OpenRouter API key (`OPENROUTER_API_KEY`) OR HuggingFace API key (`HF_API_KEY`) for cloud trial generation
- Neuronpedia API key (`NEURONPEDIA_API_KEY`) optional, raises rate limits for Circuit Tracer
- Python 3.13 runtime
- Node.js 20 for build (frontend compilation required before deployment)
- Built React frontend (pre-compiled to `frontend/dist/`)
- Environment variables: `OPENROUTER_API_KEY`, `NEURONPEDIA_API_KEY` (latter optional)
- Deployment: Container-based (Nixpacks, Heroku, Docker) or traditional Python/Node hosting
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python modules: `snake_case` (e.g., `canon_experiment.py`, `neuronpedia_client.py`, `borges_graph.py`)
- React components: `PascalCase.jsx` (e.g., `App.jsx`, `MapScreen.jsx`, `SemanticMap.jsx`)
- Utility files: `snake_case.js` (e.g., `mockData.js`, `api.js`, `useExperiment.js`)
- Hooks: `useXxx.js` (e.g., `useExperiment.js`)
- Public functions: `snake_case` (e.g., `run_experiment()`, `compile_attribution()`, `full_analysis()`)
- Private functions: `_snake_case` (leading underscore for module-private, e.g., `_get_backend()`, `_run_experiment_sync()`)
- Dataclass instances and temporary variables: `lowercase_with_underscores`
- Regular functions: `camelCase` (e.g., `fireExperiment()`, `getResults()`)
- React components: `PascalCase` (e.g., `MapScreen`, `SemanticMap`)
- Hooks: `useCamelCase` (e.g., `useExperiment`, `useTweaks`)
- Private/internal helpers: `_camelCase` (e.g., `_pollUntilDone()`, `_run()`)
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `OLLAMA_BASE`, `WINDOW_SIZE`, `MAX_NEW_POSITIONS`)
- State variables: `camelCase` in JS (e.g., `isOpen`, `currentStep`), `snake_case` in Python (e.g., `_chain_state`)
- Component props: `camelCase` (e.g., `knowledgeLayer`, `nTrials`, `injectionMode`)
- Dataclasses: `PascalCase` (e.g., `Trial`, `ExperimentRun`, `Feature`, `NLAResult`, `Step`, `CompiledGraph`)
- Type hints use full paths: `list[dict]`, `dict | None` (Python 3.10+ union syntax)
- No TypeScript; JSDoc optional but not enforced
- Implicit object shapes used directly
## Code Style
- No linter or formatter configured (eslint, prettier, black, ruff not present)
- Python: follows implicit PEP 8-ish style with 4-space indentation
- JavaScript/JSX: 2-space indentation in components and utilities
- CSS: organized with section comments using `/* ─── Label ───── */` delimiters
- None configured in the project
- No strict line length limit enforced
- Python code is typically ~100 characters per line
- JavaScript is more variable
- Python: 4 spaces
- JavaScript/JSX: 2 spaces
- CSS: 2 spaces
## Import Organization
- Not used; relative imports only (`./`, `../`)
- Backend uses absolute imports from project root (`from backend.routers import ...`)
## Error Handling
- Explicit exception handling with `try/except` and informative error messages
- HTTP errors wrapped in `HTTPException` with status code and message (see `backend/routers/experiment.py:135`)
- Runtime errors raised with context (e.g., `RuntimeError("No OPENROUTER_API_KEY or HF_API_KEY set.")`)
- Network errors: `resp.raise_for_status()` for validation, status code checks for graceful degradation
- Silent fallbacks for optional operations (e.g., warmup skipped on startup if embedding model unavailable)
- `try/catch` in async functions; errors logged or state-updated
- HTTP errors: check `res.ok`, throw `Error(await res.text())` for debugging
- Graceful error recovery: polling fallback if initial fetch times out
- State-based error display (e.g., `error` state in `useExperiment`)
## Logging
- Server startup: `print(..., flush=True)` to force immediate output (see `backend/main.py:38`)
- Error context: `print(f"Chain pre-compute failed: {e}", flush=True)` (see `backend/routers/chain.py:58`)
- Spare use of logging; print statements are debug-oriented
- Console logging for development; not visible in production UI
- Status updates via React state instead of logs (e.g., `setStatus('computing')`)
## Comments
- Explain complex algorithms or mathematical operations (e.g., UMAP normalization, statistical tests)
- Mark non-obvious workarounds or hacks (e.g., backend auto-detection fallback, warmup skipping)
- Document module purpose in docstrings
- Explain why a constraint exists (e.g., "UMAP/Numba workqueue is NOT thread-safe")
- Not enforced; Python modules use docstrings for public functions
- Python docstrings are present but minimal (see `canon_experiment.py:1-8`)
- JavaScript functions lack docstrings; logic is self-documenting
## Function Design
- Small functions for distinct responsibilities (e.g., `_normalize_projection()`, `embed_fastembed()`)
- Longer functions acceptable if they're algorithms or orchestrators (e.g., `_build_focal_scene()` at 102 lines)
- Utility functions are typically 10–40 lines
- Python: ordered positional args, followed by optional keyword args with defaults
- JavaScript: single object parameter for component props, destructured in signature
- Avoid boolean parameters for behavior divergence; use enum-style strings (e.g., `trial_type: str`, `injection_mode: str`)
- Python: typed return annotations (e.g., `-> tuple[str, float]`, `-> dict`, `-> CompiledGraph`)
- Single return value or tuple of closely related values
- Complex returns packaged in dataclasses (e.g., `Trial`, `NLAResult`, `CompiledGraph`)
- JavaScript: implicit types; return plain objects or React elements
## Module Design
- No explicit `__all__`; public functions are assumed to be those not prefixed with `_`
- Dataclasses (Trial, ExperimentRun, etc.) exported implicitly for type hints
- Default exports for React components (e.g., `export default function MapScreen(...)`)
- Named exports for utilities and hooks (e.g., `export function useTweaks(...)`, `export async function fireExperiment(...)`)
- Re-exports rare; most utilities imported directly from their source
- Not used; direct imports from source files
- Example: `import { useTweaks } from '../components/TweaksPanel'` (not from index)
## Code Organization Patterns
- Global constants at top: `OLLAMA_BASE`, `INJECTION_MODES`, `MAX_NEW_POSITIONS`
- Module-level cache/state: `_fastembed_model`, `_backend_cache`, `_chain_state`
- Helper functions prefixed with `_` before public functions
- Dataclasses near top after imports
- Main orchestration functions (`run_experiment`, `compile_attribution`, `full_analysis`) near bottom
- Props destructured in signature
- Local state (`useState`) declared first
- Event handlers and render logic inline
- Inline styles via objects for dynamic theming
- CSS classes for static design system tokens
## Design System & Styling
- Single global stylesheet (`frontend/src/styles.css`) with CSS variables
- RawBlock brutalist design system: white ground, black borders, no shadows
- Design signal colors: `--control` (black), `--test` (red), `--gold` (orange knowledge), `--link` (blue hyperlinks)
- Typography: `--display` (Archivo Black), `--ui` (Work Sans), `--mono` (Space Mono)
- Used extensively for component-specific layout and animations
- Props like `style={{ display: "grid", placeItems: "center" }}`
- Dynamic values via JavaScript (e.g., `transform={`rotate(${angle} 40 40)`}`)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Dual instrument design: Canon Ball measures semantic precision (output WHAT), Borges Graph explains causal attribution (WHY)
- Backend drives experiment execution (trials, embeddings, analysis) asynchronously; frontend is visualization layer
- Backend serves pre-built React SPA at root; frontend calls backend via `/api/*` routes
- Chain computation happens in background thread after UMAP analysis completes (synchronization via threading lock)
- Feature identifiers preserved throughout for future steering interventions
## Layers
- Purpose: Manages experiment execution, UMAP projection, statistical analysis, and attribution chain building
- Location: `backend/`
- Contains: REST routers, Pydantic schemas, configuration
- Depends on: `canon_experiment.py`, `canon_analysis.py`, `borges_graph.py`, `neuronpedia_client.py`
- Used by: React frontend via `/api/experiment` and `/api/chain` routes
- Purpose: Runs N trials with and without knowledge layer, generates model outputs, embeds via fastembed
- Location: `canon_experiment.py`
- Contains: Trial generation, backend detection (ollama vs OpenRouter), embedding computation
- Depends on: OpenRouter API (gemma-3-4b-it), fastembed (BAAI/bge-small-en-v1.5)
- Used by: `backend/routers/experiment.py` via `run_experiment()` and `load_experiment()`
- Purpose: Computes semantic space projections, dispersion metrics (euclidean/cosine), Mann-Whitney U test
- Location: `canon_analysis.py`
- Contains: UMAP dimensionality reduction, centroid computation, pairwise distance analysis
- Depends on: scikit-learn (cosine_distances), scipy (mannwhitneyu), umap-learn
- Used by: `backend/routers/experiment.py` via `full_analysis()`
- Purpose: Traces token-by-token generation with Circuit Tracer API to build causal chain
- Location: `borges_graph.py`
- Contains: `CompiledGraph` and `Step` dataclasses, Neuronpedia integration
- Depends on: `neuronpedia_client.py` for Circuit Tracer calls
- Used by: `backend/routers/chain.py` via `compile_attribution()`
- Purpose: Wraps Neuronpedia NLA (Natural Language Autoencoder) for circuit tracing and activation verbalization
- Location: `neuronpedia_client.py`
- Contains: API calls for attribution graphs, feature verbalization, batching logic (16-position cap)
- Depends on: Neuronpedia API (gemma-2-2b for Circuit Tracer, gemma-3-27b-it for NLA)
- Used by: `borges_graph.py` and `backend/routers/chain.py`
- Purpose: Visualization and control interface with 6-step rail navigation, tweaks panel
- Location: `frontend/src/`
- Contains: Screens (Concept, Setup, Map, Metrics, Modes, Focal Line), components (CannonScene, SemanticMap, TweaksPanel), hooks
- Depends on: React 18.3, Vite 6.0, backend API
- Used by: User navigates through steps, fires experiments, views results
- Purpose: Unified environment variable loading (replaces Streamlit st.secrets)
- Location: `backend/config.py`
- Contains: `.env` parsing, API key getters
- Depends on: None (pure stdlib)
- Used by: Backend routers and libraries to resolve OpenRouter and Neuronpedia keys
## Data Flow
- Frontend: React hooks (`useExperiment`, `useTweaks`) hold experiment results and UI tweaks in component state
- Backend: Results written to disk (`results/`) to survive server restarts; chains built in background thread with lock-protected state dict
- UMAP computation serialized with `_umap_lock` (Numba not thread-safe)
## Key Abstractions
- Purpose: Holds N control trials and N test trials with embeddings
- Examples: `canon_experiment.run_experiment()` returns `ExperimentData` namedtuple
- Pattern: Trials are serialized to `results/experiment.json` and reloaded by analysis and API endpoints
- Purpose: Quantifies "landing zone" tightness (coherence of semantic outputs)
- Examples: `canon_analysis.compute_dispersion()` returns euclidean/cosine distances to centroid
- Pattern: Control vs test dispersion ratio is the primary WHAT measurement (tightening %)
- Purpose: Experimental variable controlling how knowledge layer is introduced into model
- Examples: `system_user`, `interleave`, `template`, `cot_priming` (defined in `canon_experiment.INJECTION_MODES`)
- Pattern: Each mode is a different prompt engineering strategy; `FireRequest.injection_mode` selects which to run
- Purpose: Autoregressive chain of attribution steps, preserving feature IDs for steering
- Examples: `borges_graph.CompiledGraph` holds list of `Step` objects
- Pattern: Each step has token, context_length, and optional subgraph; `all_feature_ids()` extracts SAE indices for future interventions
- Purpose: Maps Circuit Tracer subgraph + NLA verbalizations into left-middle-right visualization
- Examples: `{inputs, converge, focus, answer, diverge}` objects
- Pattern: Inputs = prompt tokens, converge = top features (colored by knowledge influence), focus = predicted token, diverge = NLA descriptions
## Entry Points
- Location: `backend/main.py`
- Triggers: `python3 -m uvicorn backend.main:app --port 8000 --reload`
- Responsibilities: CORS setup, router mounting, warmup (fastembed pre-load), SPA serving
- Location: `backend/routers/experiment.py:fire_experiment()`
- Triggers: Frontend `POST /api/experiment/fire`
- Responsibilities: Run trials, analyze, save to disk, kick off background chain building, return immediate response
- Location: `backend/routers/chain.py:get_chain_status()`
- Triggers: Frontend `GET /api/chain/status` (poll loop in `useExperiment` hook)
- Responsibilities: Return thread-safe chain computation state (idle/computing/ready/failed)
- Location: `frontend/src/main.jsx` → `App.jsx`
- Triggers: Browser loads `http://localhost:5173` (dev) or production root
- Responsibilities: Initialize step navigation, mock data, tweak state; render 6-step rail
## Error Handling
- **Missing Experiment Results:** `GET /api/experiment/results` returns 404 if `experiment.json` not found; frontend shows placeholder mock data
- **Chain Computation Failure:** Background thread catches exception, sets `_chain_state["error"]` and `state="failed"`; frontend displays error message instead of scene
- **API Key Missing:** Health endpoint checks both keys; if missing, experiment will fail with runtime error
- **UMAP Lock Timeout:** Not explicitly handled; would block forever if thread holding lock crashes (known limitation)
- **NLA Timeout:** 90-second timeout on Neuronpedia requests; if exceeded, scene uses placeholder node
- **Incomplete Subgraph:** If Circuit Tracer returns no feature nodes, scene shows "(attribution unavailable)" placeholder
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
