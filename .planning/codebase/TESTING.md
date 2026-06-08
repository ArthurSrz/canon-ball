# Testing Patterns

**Analysis Date:** 2026-06-08

## Test Framework

**Runner:**
- No test framework configured (pytest, jest, vitest not present)
- No test files detected in source directories

**Assertion Library:**
- Not applicable

**Run Commands:**
- No test commands available

## Test File Organization

**Location:**
- Not applicable — no tests present

**Naming:**
- Not applicable

**Structure:**
- Not applicable

## Current Testing Status

**No automated testing framework is configured in this project.** The codebase relies on:
1. **Manual testing** during development (running the FastAPI server and React frontend)
2. **Endpoint validation** via browser or curl (health check at `GET /health`, API endpoints at `/api/experiment/fire`, `/api/experiment/results`, etc.)
3. **Mock data** for frontend development (`frontend/src/mockData.js`)

## Manual Testing Approach

**Backend (FastAPI):**
- Run via `python3 -m uvicorn backend.main:app --port 8000 --reload`
- Health check: `GET /api/health` returns `{"status": "ok", "openrouter_key_set": bool, "neuronpedia_key_set": bool}`
- Experiment endpoint: `POST /api/experiment/fire` with FireRequest payload (see `backend/schemas.py`)
- Results retrieval: `GET /api/experiment/results` after experiment completes
- Chain endpoints: `GET /api/chain/status`, `GET /api/chain/results`, `POST /api/chain/trace`, `POST /api/chain/focal`

**Frontend (React/Vite):**
- Run via `cd frontend && npm run dev`
- Vite proxy at `vite.config.js` routes `/api/*` to `http://localhost:8000`
- Mock data in `frontend/src/mockData.js` allows testing UI without a running backend
- Components tested by visual inspection during dev

**Integration Testing:**
- End-to-end flow: fire experiment → wait for UMAP + chain computation → retrieve results
- Polling in `useExperiment.js` polls `/api/experiment/results` every 5 seconds for up to 6 minutes
- Chain computation runs in background thread (see `backend/routers/chain.py:30-60`)

## Data Generation for Testing

**Mock Data Shape (`frontend/src/mockData.js`):**
- Synthesized experiment results matching real metrics from `injection_mode_results.md`
- PRNG seeded for stable results across reloads
- Includes per-trial landing positions, centroids, and textual outputs
- Used for developing UI without waiting for actual experiment runs

Example mock structure:
```javascript
const MOCK_DATA = {
  setup: {
    prompt: "...",
    knowledgeLayer: "...",
    nTrials: 8,
    model: "gemma-3-4b-it",
    embedder: "bge-small-en-v1.5",
  },
  control: [...],
  test: [...],
  comparison: {
    controlMeanDispersion: ...,
    testMeanDispersion: ...,
    dispersionRatio: ...,
    // ...
  }
}
```

## Testing Patterns in Code

**Backend Request Validation:**
- Pydantic models auto-validate incoming JSON (see `backend/schemas.py`)
- `FireRequest`, `TraceRequest`, `FocalRequest` use ConfigDict with alias generators to accept camelCase from frontend and convert to snake_case internally

Example from `backend/schemas.py:7-12`:
```python
class FireRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    prompt: str
    knowledge_layer: str
    n_trials: int = 8
    injection_mode: str = "template"
```

**Error Boundary Testing:**
- `_pollUntilDone()` in `useExperiment.js` handles slow or failed requests by polling with 15-second timeout before switching to polling mode
- Backend 404 responses for missing results trigger error state in frontend

Example from `backend/routers/experiment.py:130-137`:
```python
@router.get("/results")
def get_results():
    exp_path = RESULTS_DIR / "experiment.json"
    analysis_path = RESULTS_DIR / "analysis.json"
    if not exp_path.exists():
        raise HTTPException(404, "No experiment results found. Fire an experiment first.")
    if not analysis_path.exists():
        raise HTTPException(404, "Analysis not ready yet. Still computing.")
```

**State Management Testing (Frontend):**
- `useExperiment()` hook tracks states: `'idle' | 'firing' | 'polling' | 'done' | 'error'`
- Error propagated through `error` state variable, displayed in UI
- Race condition handling: promise race between immediate fire response and timeout → polling fallback

Example from `hooks/useExperiment.js:19-38`:
```javascript
const result = await Promise.race([
  fetchPromise.catch(async () => {
    setStatus('polling')
    return _pollUntilDone()
  }),
  new Promise((resolve, reject) => {
    setTimeout(async () => {
      setStatus('polling')
      try { resolve(await _pollUntilDone()) }
      catch (e) { reject(e) }
    }, 15000)
  }),
])
```

## Configuration & Environment Testing

**Backend Configuration:**
- `.env` file (not tracked) or `.env.example` for template
- Keys tested on startup via `/health` endpoint
- Config module (`backend/config.py`) loads environment variables with no python-dotenv dependency

Example from `backend/config.py:10-23`:
```python
def _load_dotenv():
    """Load .env file if present (no dependency on python-dotenv)."""
    for candidate in [Path(".env"), Path(__file__).resolve().parent.parent / ".env"]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                # ... parse key=value ...
```

**Backend Startup Warmup:**
- `@app.on_event("startup")` pre-loads fastembed model in executor thread (see `backend/main.py:29-41`)
- Warmup silently skipped if model unavailable (graceful degradation)
- Numba workqueue thread-safety issues handled with `_umap_lock` (see `backend/routers/experiment.py:18-19`)

Example from `backend/main.py:29-41`:
```python
@app.on_event("startup")
async def warmup():
    """Pre-load fastembed model at startup so first experiment doesn't cold-start."""
    import asyncio
    loop = asyncio.get_event_loop()
    def _warm():
        try:
            from canon_experiment import _get_fastembed
            _get_fastembed()
            print("Embedding model warmed up.", flush=True)
        except Exception as e:
            print(f"Warmup skipped: {e}", flush=True)
    loop.run_in_executor(None, _warm)
```

## What is NOT Tested

**Untested areas:**
- `canon_experiment.py` trial generation logic (multiple injection modes, chat backends)
- `canon_analysis.py` UMAP projection and statistical tests
- `borges_graph.py` attribution chain compilation
- `neuronpedia_client.py` API integration with Neuronpedia (requires valid API key and external service)
- Frontend component rendering (visual testing only)
- CSS layout and animations
- Browser compatibility

**Risk:** Any changes to these modules could introduce bugs without automated validation.

## Recommended Testing Additions

For future test coverage, prioritize:
1. **Unit tests for `canon_analysis.py`**: Dispersion metrics, Mann-Whitney U test, UMAP normalization (critical statistics)
2. **Integration tests for experiment flow**: End-to-end test with mock API responses
3. **Component snapshot tests**: MapScreen, FocalLineScreen rendering with different data
4. **API contract tests**: Verify Pydantic models accept/reject valid/invalid inputs
5. **Chain computation tests**: Mock Neuronpedia responses, validate CompiledGraph structure

---

*Testing analysis: 2026-06-08*
