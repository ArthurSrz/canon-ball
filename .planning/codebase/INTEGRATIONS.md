# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**LLM Completion (Trial Generation):**
- OpenRouter (primary cloud backend)
  - Service: `https://openrouter.ai/api/v1/chat/completions`
  - Model: `google/gemma-3-4b-it`
  - SDK/Client: `requests` library
  - Auth: `OPENROUTER_API_KEY` env var (required if no HuggingFace key)
  - Implementation: `canon_experiment.chat_openrouter()` in `canon_experiment.py`
  - Headers: `Authorization: Bearer {key}`, `HTTP-Referer`, `X-Title`

- Hugging Face router (fallback)
  - Service: `https://router.huggingface.co/featherless-ai/v1/chat/completions`
  - Model: `google/gemma-2-2b-it` via Featherless AI
  - Auth: `HF_API_KEY` env var (optional, used if set instead of OpenRouter)
  - Implementation: `canon_experiment._chat_hf()` in `canon_experiment.py`
  - Note: Normalizes system role into user role (framework limitation)

**Embedding (Output Projection):**
- OpenAI-compatible fastembed (cloud backend)
  - Model: `BAAI/bge-small-en-v1.5` (local download on first use)
  - SDK/Client: `fastembed` Python package
  - Auth: None required (model is public)
  - Implementation: `canon_experiment.embed_fastembed()` in `canon_experiment.py`
  - Warmup: Pre-loaded at FastAPI startup via `backend/main.py` warmup hook to avoid cold starts

**Neuronpedia NLA (Activation Verbalization):**
- Service: `https://www.neuronpedia.org/api/nla/`
- Models: `gemma-3-27b-it`, `gemma-2-2b`, `llama-3.3-70b` (verbalization layers)
- SDK/Client: `requests` library
- Auth: `NEURONPEDIA_API_KEY` header (optional; auth raises rate limits)
- Endpoints:
  - `GET /api/nla/sources` - List available (modelId, nlaSourceId, layerNum) pairs
  - `POST /api/nla/explain` - Verbalize activations at token positions (16-position batch limit)
  - `POST /api/nla/completion` - Generate response with NLA metadata (best-effort, can 500)
  - `POST /api/nla/attributions` - Fetch per-token attribution graphs (returns S3 URL)
- Implementation: `neuronpedia_client.py` module
  - `neuronpedia_client.list_sources()` - List NLA sources
  - `neuronpedia_client.verbalize_activations()` - Batch explain with auto-batching (capped 16/request)
  - `neuronpedia_client.fetch_attribution_subgraph()` - Download and parse S3 attribution JSON
  - `neuronpedia_client._explanation_meta()` - Get circuit tracer metadata with S3 URL
- Circuit Tracer Constraints:
  - Model: gemma-2-2b only
  - Prompt cap: 64 tokens (sliding window when exceeded)
  - Rate limit: 30 requests/hour (with API key: raised)

**Neuronpedia S3 (Attribution Graph Data):**
- Service: AWS S3 (Neuronpedia's data store)
- Auth: None (public URLs returned by attribution endpoints)
- Usage: Fetch compiled attribution graphs as JSON blobs
- Implementation: `neuronpedia_client.fetch_attribution_subgraph(s3url)` - Downloads and parses
- Rate limit: None observed (S3 is direct public fetch)

## Local Services (Optional)

**Ollama (Local LLM & Embedding, Fallback):**
- Base: `http://localhost:11434`
- Models: `qwen2.5:3b` (chat), `bge-m3` (embedding)
- Auth: None required
- Auto-detection: `canon_experiment._get_backend()` probes `localhost:11434/api/tags` with 1.5s timeout; if offline, falls back to cloud
- Endpoints:
  - `POST /api/chat` - Chat completion (local model)
  - `POST /api/embed` - Embedding (local model)
- Implementation: `canon_experiment.chat_ollama()`, `canon_experiment.embed_ollama()`
- Override: Set `CANON_BACKEND=cloud` or `=ollama` to force backend

## Data Storage

**File System (Local Disk):**
- Location: `results/` directory (created on-demand)
- Format: JSON files
- Contents:
  - `chain_control.json` - Attribution chain for control (baseline) flow
  - `chain_test.json` - Attribution chain for test (knowledge layer) flow
  - Experiment results (UMAP projections, trial outputs, embeddings)
- Persistence: Across server restarts (module load checks disk state in `backend/routers/chain.py`)
- No cleanup or retention policy configured

**In-Memory Cache:**
- `_fastembed_model` - Global singleton embedding model (cached in `canon_experiment._get_fastembed()`)
- `_backend_cache` - Cached backend detection result (avoids repeated localhost probes)
- `_chain_state` - Chain computation progress state (in `backend/routers/chain.py`)

## Authentication & Identity

**Auth Provider:** None. Service uses API keys but no user authentication.

**API Key Management:**
- OpenRouter: `OPENROUTER_API_KEY` env var (required for cloud LLM)
- HuggingFace: `HF_API_KEY` env var (optional fallback to OpenRouter)
- Neuronpedia: `NEURONPEDIA_API_KEY` env var (optional; auth only raises rate limits)
- Load logic: `backend/config.py` reads from `.env` file or `os.environ`

## Monitoring & Observability

**Error Tracking:** None detected. Errors logged to stdout/stderr.

**Logs:**
- Backend: Print statements to stdout with `flush=True` (e.g., embedding warmup, chain pre-compute status)
- Frontend: Browser console logs (no centralized logging)
- No structured logging framework (no loguru, structlog, etc.)

## CI/CD & Deployment

**Hosting:**
- Container-based: Nixpacks, Heroku, or Docker
- CICD: Specified in `nixpacks.toml` (build steps for Python + Node + frontend compilation)
- Entry point: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

**Build Steps:**
1. Install Node.js 20 (Nixpacks)
2. Install Python dependencies: `pip install -r requirements.txt`
3. Build frontend: `cd frontend && npm install && npm run build` → outputs to `frontend/dist/`
4. Start server: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

**Frontend Build Output:**
- Location: `frontend/dist/` (mounted as static files in FastAPI)
- Static assets: `frontend/dist/assets/` (CSS, JS bundles)
- SPA fallback: All routes serve `frontend/dist/index.html` for React router

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - OpenRouter API key for LLM trial generation (required if HF_API_KEY not set)

**Optional env vars:**
- `HF_API_KEY` - HuggingFace API key (fallback to OpenRouter)
- `NEURONPEDIA_API_KEY` - Neuronpedia API key (raises rate limits for Circuit Tracer)
- `CANON_BACKEND` - Force backend: "cloud" or "ollama" (default: auto-detect)

**Secrets location:**
- Development: `.env` file (git-ignored, see `.env.example`)
- Production: Environment variables set by deployment platform (Heroku, Railway, etc.)
- No secrets manager integration (AWS Secrets, Vault, etc.)

## Webhooks & Callbacks

**Incoming:** None detected.

**Outgoing:** None detected.

---

*Integration audit: 2026-06-08*
