# Codebase Concerns

**Analysis Date:** 2026-06-08

## Tech Debt

**Dual code paths: Streamlit + FastAPI/React**
- Issue: Legacy Streamlit implementation (`app.py`, `pages/`, `shared_sidebar.py`, `html_components.py`) still in codebase while new FastAPI+React stack is active
- Files: `app.py`, `pages/1_Canon_Ball.py`, `pages/2_Borges_Graph.py`, `html_components.py` (1,139 lines), `shared_sidebar.py`
- Impact: Maintenance burden, unclear which path is canonical, testing matrix doubled
- Fix approach: Complete Streamlit removal once React UI is stable; establish feature parity matrix first

**Global mutable state in backend routers**
- Issue: Thread-safe state dicts managed manually with locks rather than using a proper state management layer
- Files: `backend/routers/chain.py` (lines 16-22, 64-66), `backend/routers/experiment.py` (line 19)
- Impact: Daemon thread in chain.py can fail silently without proper task tracking; state loss on server restart
- Fix approach: Migrate to async task queue (Celery/RQ) or FastAPI BackgroundTasks; persist state to Redis/database

**Asyncio/threading mixing in experiment endpoint**
- Issue: `fire_experiment` uses `asyncio.get_event_loop().run_in_executor()` to offload sync work, but executor can become bottleneck; UMAP/Numba thread conflict acknowledged but not systematized
- Files: `backend/routers/experiment.py` (lines 63-66, 114)
- Impact: Blocking UMAP lock during chain computation can leave client hanging; poor observability
- Fix approach: Use proper async/await or dedicated worker pool; consider UMAP GPU backend

## Known Bugs

**Backend detection race condition**
- Symptoms: First call to `_get_backend()` may block 1.5s (Ollama probe timeout) on cloud deployments
- Files: `canon_experiment.py` (lines 34-56)
- Trigger: Environment with no local Ollama and CANON_BACKEND not set; first experiment or first embedding call
- Workaround: Set `CANON_BACKEND=cloud` or `CANON_BACKEND=ollama` explicitly in .env
- Fix approach: Async health check at startup rather than lazy detection; cache across process

**Chain state not invalidated on new experiment**
- Symptoms: Firing a second experiment without clearing results shows old chains
- Files: `backend/routers/chain.py` (lines 26-27, 30-60)
- Trigger: If chain pre-compute fails partially, state remains "computing" and never recovers
- Workaround: Manual server restart or direct file deletion
- Fix approach: Reset state before starting new chains; add explicit invalidation endpoint

**Missing error propagation in fire endpoint**
- Symptoms: If UMAP projection fails or analysis crashes, client receives 500 with generic message
- Files: `backend/routers/experiment.py` (lines 104-127)
- Trigger: Malformed trial data, OOM on large projections, missing fastembed model
- Workaround: Check logs; frontend defaults to mock data on any 500
- Fix approach: Add detailed error context to HTTP response; validate trial structure before UMAP

**Neuronpedia API silent failures**
- Symptoms: Circuit Tracer or NLA explain calls may timeout/fail without retry; partial results kept silently
- Files: `neuronpedia_client.py` (lines 225-232, 288-293)
- Trigger: GPU queue full (503), network blip, rate limit (429 not explicitly handled)
- Workaround: Graceful degradation — converge/diverge fallbacks render placeholders
- Fix approach: Add explicit retry with exponential backoff; surface busy/rate-limited state to client

## Security Considerations

**No API key rotation or expiration tracking**
- Risk: OpenRouter and Neuronpedia keys stored in .env; compromise persists indefinitely
- Files: `backend/config.py`, `.env.example` (template only, no secrets)
- Current mitigation: .env excluded from git; keys in environment variables only
- Recommendations: 
  - Implement key rotation endpoint that updates backend without restart
  - Add key age tracking and warn when > 90 days old
  - Use short-lived tokens (if providers support)
  - Consider Secret Manager integration (AWS Secrets Manager, HashiCorp Vault)

**CORS wide open**
- Risk: Credentials can be stolen by malicious script on any origin
- Files: `backend/main.py` (lines 18-23)
- Current mitigation: Only fires to localhost during development; production should restrict
- Recommendations: 
  - Set `allow_origins` to explicit domain list in production
  - Add environment variable `ALLOWED_ORIGINS` for deployment flexibility
  - Document security posture in README

**No rate limiting on experiment endpoints**
- Risk: Attacker can exhaust OpenRouter quota or Neuronpedia GPUs
- Files: `backend/routers/experiment.py`, `backend/routers/chain.py`
- Current mitigation: None
- Recommendations:
  - Add slowdown decorator (1 request per IP per 5 minutes for /fire)
  - Track quota per API key; reject if near limit
  - Return 429 with Retry-After header

**Prompt injection via knowledge_layer**
- Risk: User-provided knowledge layer passed directly to LLM without sanitization
- Files: `backend/routers/experiment.py`, `canon_experiment.py` (message assembly)
- Current mitigation: None; model is small (gemma-3-4b), risk mitigated by scale
- Recommendations:
  - Log all prompts and knowledge layers for audit trail
  - Add optional content filter (DAN/jailbreak detection)
  - Document that knowledge layer content is user-controlled

## Performance Bottlenecks

**UMAP projection on large embeddings**
- Problem: With 12 trials × N chunks × 2 (control+test), can hit thousands of points; UMAP fit is O(N log N) but has high constants
- Files: `canon_analysis.py` (lines 101-140), `backend/routers/experiment.py` (lines 114-115)
- Cause: No sampling or dimensionality reduction before UMAP; Numba JIT on first run adds ~2s latency
- Improvement path:
  - Cache UMAP model across requests (fit once, transform new)
  - Implement GPU UMAP via cuML for >1000 points
  - Add streaming/chunked analysis for very large experiments
  - Warm up Numba on server startup

**Embeddings computed twice: once for analysis, once for frontend**
- Problem: Trial embeddings stored but re-normalized in `_normalize_projection`
- Files: `backend/routers/experiment.py` (lines 22-59)
- Cause: Analysis receives raw embeddings; projection must normalize to [0-100] range
- Improvement path: Pre-normalize during trial creation or cache normalized projections

**Circuit Tracer spinning window approximation**
- Problem: `_sliding_window` uses word count (splits on whitespace) to estimate tokens, but actual tokenization differs
- Files: `borges_graph.py` (lines 104-110)
- Cause: No access to gemma-2-2b tokenizer locally; estimation causes context loss
- Improvement path:
  - Use `transformers.AutoTokenizer` with gemma-2-2b weights offline
  - Or push tokenization to Neuronpedia API (add /api/tokenize endpoint)

**Fastembed model coldstart**
- Problem: First embedding call downloads ~100MB bge-m3 model and compiles Rust extensions
- Files: `canon_experiment.py` (lines 68-73), `backend/main.py` (lines 30-41)
- Cause: No preload in Docker; lazy import on first trial
- Improvement path:
  - Ensure warmup endpoint runs and completes before accepting requests
  - Ship model artifact in Docker image (vs. downloading)
  - Add health check that verifies model is loaded

## Fragile Areas

**Borges graph token extraction brittle**
- Files: `borges_graph.py` (lines 113-129)
- Why fragile: Parses logit node label with regex `r'^Output\s*"(.+?)"\s*\(p='` and fallback string splitting; if Neuronpedia changes label format, breaks silently
- Safe modification:
  - Add structured output request to Circuit Tracer API (return token + prob as JSON fields)
  - Add comprehensive logging of label format for each step
  - Fall back to empty string, not "?", when parse fails (clearer to user)
- Test coverage: No unit tests for token extraction; only E2E via full experiment

**NLA result merging across batches**
- Files: `neuronpedia_client.py` (lines 219-240)
- Why fragile: Batches results by position into a dict, then converts to list; if positions returned out-of-order or duplicated, silent data loss
- Safe modification:
  - Assert position uniqueness per batch
  - Add explicit batch ordering check (positions must be sorted)
  - Log any skipped positions
- Test coverage: No validation of position continuity

**Focal line scene building with missing subgraph**
- Files: `backend/routers/chain.py` (lines 125-227)
- Why fragile: If Circuit Tracer fails, subgraph is None; code has fallback placeholders but merges with optional attribution with no validation
- Safe modification:
  - Separate converge/diverge logic into helper functions with clear None handling
  - Add explicit checks for each optional field (subgraph, nla_result, attrib labels)
  - Log which fallback was used so UI can surface "attribution unavailable" clearly
- Test coverage: No tests for null/missing subgraph case

**Thread-safe state in chain.py**
- Files: `backend/routers/chain.py` (lines 16-22, 60, 65-66)
- Why fragile: Dict updates in daemon thread; if two experiments fire concurrently, state is corrupted
- Safe modification:
  - Use `threading.RLock()` and wrap entire state access
  - Or migrate to asyncio with proper task management
  - Add concurrent experiment rejection at router level
- Test coverage: No concurrency tests

## Scaling Limits

**Single Neuronpedia API key shared across all requests**
- Current capacity: 30 requests/hour for Circuit Tracer; 16 new positions per /explain request
- Limit: With 12 trials + chains (2 prompts × ~6 tokens = ~12 more requests), each experiment uses ~12-16 of the 30 quota
- Scaling path:
  - Implement request queuing with daily quota tracking
  - Allow multi-key configuration (round-robin across keys)
  - Fall back to NLA-only (no Circuit Tracer) when quota exhausted

**UMAP/Numba single-threaded bottleneck**
- Current capacity: ~500 embeddings (12 trials × 40 chunks) fit comfortably; >2000 points slow
- Limit: Numba JIT is single-threaded; lock serializes all UMAP calls
- Scaling path:
  - Use GPU UMAP (cuML) for >1000 points
  - Implement model caching + incremental fits (no recompute on new experiment)
  - Or move to dedicated analysis service

**Embeddings vector size → memory**
- Current: bge-m3 produces 384-dim vectors; 12 trials × 50 chunks × 384 × 8 bytes = ~1.8 MB per experiment
- Limit: No issue for typical use; would hit memory ceiling around 10k concurrent embeddings
- Scaling path:
  - Archive old experiments to S3/PostgreSQL
  - Implement pagination for historical results

## Dependencies at Risk

**umap-learn + Numba**
- Risk: Numba thread-safety issues documented; UMAP development is sparse (last release 0.4.6 ~1 year old)
- Impact: Future Python versions may break Numba; UMAP bugs stay unfixed
- Migration plan:
  - Evaluate cuML (RAPIDS GPU-accelerated) as drop-in replacement
  - Or use parametric t-SNE from scikit-learn (slower but pure-Python)
  - Maintain local fork of UMAP if critical to product

**OpenRouter API stability**
- Risk: Small API provider; could shut down or change pricing without notice
- Impact: All experiment generation would fail; no fallback model
- Migration plan:
  - Support multiple model backends (Ollama local, LM Studio, Together AI)
  - Implement model abstraction layer with provider fallthrough
  - Cache responses so platform outage doesn't block reading results

**fastembed library**
- Risk: Rust bindings + active development; occasional breaking changes
- Impact: Embedding endpoints break on new version; can't update dependencies
- Migration plan:
  - Pin to exact version in requirements.txt (currently unpinned)
  - Test against next minor version in CI before auto-upgrading
  - Consider pure-Python fallback (sentence-transformers)

## Missing Critical Features

**No persistent job queue**
- Problem: Chain computation is daemon thread; if server crashes mid-compute, work is lost
- Blocks: Production deployment; users can't safely navigate away during experiment
- Fix: Replace daemon thread with Celery/RQ; store task ID in frontend state

**No explicit experiment validation**
- Problem: No check for min/max N trials, prompt length, knowledge layer size before firing
- Blocks: Can accept pathological inputs (empty prompt, 1000-trial experiment)
- Fix: Add request validator with sensible constraints (8-32 trials, <4096 token prompts)

**No result versioning or comparison**
- Problem: GET /results overwrites old results; can't compare two experiments
- Blocks: Can't build a suite of experiments or show progression over time
- Fix: Add result ID (timestamp + hash); store in results/ directory; add comparison endpoint

## Test Coverage Gaps

**Token extraction from Circuit Tracer logits**
- What's not tested: The regex and fallback parsing in `borges_graph.py` lines 119-124
- Files: `borges_graph.py`
- Risk: Silent failures when label format changes; "?" tokens break downstream analysis
- Priority: High

**NLA batch merging and position continuity**
- What's not tested: Duplicate/out-of-order position handling in `neuronpedia_client.py` lines 234-237
- Files: `neuronpedia_client.py`
- Risk: Data loss when batches return positions out-of-order
- Priority: High

**UMAP projection under concurrency**
- What's not tested: Behavior when two experiments fire simultaneously and hit _umap_lock
- Files: `backend/routers/experiment.py`
- Risk: Race condition or deadlock; second request silently queued indefinitely
- Priority: Medium

**Focal line scene building with missing attributions**
- What's not tested: All combinations of (subgraph=None, nla_result=None, both=None)
- Files: `backend/routers/chain.py` lines 125-227
- Risk: Placeholder fallbacks may not render correctly or could error
- Priority: Medium

**Frontend error handling for failed fire endpoint**
- What's not tested: React component behavior when /api/experiment/fire returns 500
- Files: `frontend/src/hooks/useExperiment.jsx` (likely)
- Risk: Frontend may crash or show stale mock data without warning
- Priority: Medium

**Injection mode tokenization edge cases**
- What's not tested: `assemble_messages` with edge cases (empty knowledge layer, very long prompt)
- Files: `canon_experiment.py` lines 196-225
- Risk: Interleave mode can produce malformed prompts if splitting fails
- Priority: Low

---

*Concerns audit: 2026-06-08*
