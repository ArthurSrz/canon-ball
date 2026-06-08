# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.13 - Backend, experiment engine, analysis, and library code
- JavaScript (ES6+/TypeScript-ready) - Frontend React components and application logic

**Secondary:**
- CSS3 - RawBlock brutalist design system in `frontend/src/styles.css`
- JSON - Configuration and data interchange

## Runtime

**Environment:**
- Python 3.13 (specified by CICD/Nix, see `nixpacks.toml`)
- Node.js 20 (for frontend build, specified in `nixpacks.toml`)

**Package Manager:**
- Python: `pip` with `requirements.txt`
- Node.js: `npm` with `package-lock.json`
- Lockfile: Both present and committed

## Frameworks

**Core Backend:**
- FastAPI 0.115.0+ - REST API framework, CORS middleware, request/response handling
- Uvicorn 0.32.0+ - ASGI server for FastAPI

**Core Frontend:**
- React 18.3.1 - UI framework
- Vite 6.0.0 - Build tool and dev server with proxy support for API calls

**Testing:**
- None configured (no test framework found in dependencies)

**Build/Dev:**
- Vite with `@vitejs/plugin-react` 4.3.0 - React fast refresh and bundling
- TypeScript types available: `@types/react`, `@types/react-dom` (dev dependencies)

## Key Dependencies

**Critical:**
- `numpy` - Numerical arrays for embedding operations and UMAP projection
- `scikit-learn` - UMAP dimensionality reduction, Mann-Whitney U statistical tests
- `scipy` - Statistical functions (Mann-Whitney U)
- `umap-learn` - Dimensionality reduction for semantic projection visualization
- `fastembed` (BAAI/bge-small-en-v1.5 model) - Local embedding model for cloud backend
- `requests` - HTTP client for OpenRouter, Hugging Face, Neuronpedia, Ollama APIs

**Infrastructure:**
- `fastapi` - HTTP server with automatic JSON serialization, CORS, type validation
- `pydantic` - Request/response validation with camelCase alias support
- `uvicorn` - ASGI application server with reload and host binding support

## Configuration

**Environment:**
- `.env` file (not committed, see `.env.example`)
- Environment variables read in `backend/config.py` without external dependencies
- Supports manual or automatic detection of backend (ollama vs. cloud)
- Override via `CANON_BACKEND` env var: "cloud" or "ollama" (default: auto-detect)

**Key Configuration Files:**
- `backend/config.py` - Centralized config for API keys (OpenRouter, Neuronpedia, HuggingFace)
- `requirements.txt` - Python dependencies (pinned to minimum versions, not locked)
- `frontend/package.json` - Node dependencies with caret ranges (allow patch/minor updates)
- `frontend/vite.config.js` - Vite dev server with API proxy to `http://localhost:8000`
- `nixpacks.toml` - CICD build configuration for Nixpacks deployment
- `Procfile` - Heroku/Procfile-compatible deployment: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

## Platform Requirements

**Development:**
- Python 3.13 with pip
- Node.js 20 with npm
- Local Ollama installation optional (auto-detected for local embedding/chat)
- OpenRouter API key (`OPENROUTER_API_KEY`) OR HuggingFace API key (`HF_API_KEY`) for cloud trial generation
- Neuronpedia API key (`NEURONPEDIA_API_KEY`) optional, raises rate limits for Circuit Tracer

**Production:**
- Python 3.13 runtime
- Node.js 20 for build (frontend compilation required before deployment)
- Built React frontend (pre-compiled to `frontend/dist/`)
- Environment variables: `OPENROUTER_API_KEY`, `NEURONPEDIA_API_KEY` (latter optional)
- Deployment: Container-based (Nixpacks, Heroku, Docker) or traditional Python/Node hosting

**Database:** None. All data stored as JSON files in `results/` directory (local filesystem).

**Storage:** No dedicated file storage — embeddings, graphs, and analysis results persisted as `.json` files on disk.

---

*Stack analysis: 2026-06-08*
