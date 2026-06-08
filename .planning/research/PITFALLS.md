# Domain Pitfalls

**Project:** Canon Ball
**Domain:** LLM interpretability experiment instrument (attribution graphs, semantic dispersion, FastAPI + React)
**Researched:** 2026-06-08
**Confidence:** HIGH (all pitfalls grounded in codebase evidence from CONCERNS.md + domain verification)

---

## Critical Pitfalls

Mistakes that cause partial-rewrites, data corruption, or the instrument giving wrong answers silently.

---

### Pitfall 1: Differential graph compares stale chains

**What goes wrong:** The differential Borges view renders side-by-side control vs. test attribution graphs, but the chains were computed for a previous experiment. The semantic dispersion metrics show fresh results while the graph shows old attribution — the researcher reads a contradiction that doesn't exist in the data.

**Why it happens:** Chain state in `backend/routers/chain.py` is not invalidated when a new experiment fires. The background daemon starts computing new chains only after `/api/experiment/fire` returns, but there is no gate that blocks the differential view from rendering until both new chains are ready. If partial failure leaves state as `"computing"` forever, the old completed result is served instead.

**Consequences:** The entire instrument's research value is undermined. A researcher could conclude "this knowledge layer activates token X" when they're looking at a completely different experiment. Silent wrongness is the worst failure mode for a research tool.

**Prevention:**
- Before starting any new experiment, atomically reset chain state to `{"status": "invalidated", "control": null, "test": null}` — do this as the first operation in `/api/experiment/fire`, before spawning background work.
- Add a `chain_experiment_id` field that mirrors `experiment_id`. The differential view must refuse to render if `chain_experiment_id != experiment_id`.
- Add a hard timeout (e.g., 5 minutes) after which `"computing"` transitions to `"failed"` with an error message.

**Detection:** Fire two experiments in sequence without refreshing the page. If the chain view doesn't blank between fires, the invalidation is missing.

**Phase:** Chain state invalidation fix — address before or alongside differential graph feature. A differential graph built on stale chains is worse than no differential graph.

---

### Pitfall 2: Attribution graph format change breaks token extraction silently

**What goes wrong:** `borges_graph.py` extracts token labels from Circuit Tracer logit nodes using a regex (`r'^Output\s*"(.+?)"\s*\(p='`) and a fallback string split. Neuronpedia changes the label format in an API update. The regex fails silently, falling back to `"?"` tokens. The differential graph renders with `"?"` in every node — the researcher assumes it's a rendering bug, not a data bug.

**Why it happens:** The Circuit Tracer API is external and unversioned from the client's perspective. There is no schema validation on the response, no test for the extraction path, and the fallback is too permissive (`"?"` looks like a valid placeholder, not an error).

**Consequences:** All attribution chain work is meaningless. The Focal Line view and the new differential graph both display nonsense. No error is raised. This has likely already caused invisible data quality issues.

**Prevention:**
- Add a schema assertion on the raw Circuit Tracer response before processing: if the expected label structure is absent, raise explicitly, don't fall back.
- Replace `"?"` fallback with `None`/empty and propagate visibly to the UI as "attribution unavailable."
- Add a unit test for `_extract_token_label` that covers the current format + a regression case for the previous format.
- Log the raw label string for every extraction, keyed by experiment ID, so format changes are detectable post-hoc.

**Detection:** Run the token extraction function against a saved Circuit Tracer response fixture. If the test is absent, the risk is active.

**Phase:** Must be addressed before building the differential graph. The differential view depends on token labels to align nodes between control and test graphs; `"?"` alignment is meaningless.

---

### Pitfall 3: Differential graph node alignment by position, not by semantic identity

**What goes wrong:** When building a side-by-side or overlaid diff of control vs. test attribution graphs, the implementation aligns nodes by their index position in the graph rather than by what they represent (the feature/token they correspond to). Since knowledge injection changes the circuit — new features activate, old ones drop out — positional alignment produces nonsense diffs. Node 3 in the control graph is not the same concept as node 3 in the test graph.

**Why it happens:** This is the canonical mistake in attribution graph diffing. It's natural to loop over two lists of nodes in parallel. The correct approach requires a shared identity key — the SAE feature index (`feature` field already preserved in `CompiledGraph`) or the token position in the original prompt.

**Consequences:** The differential view shows activations as "added" or "removed" when they've simply reordered. A researcher might conclude the knowledge layer suppressed a feature that is actually still present but at a different graph position.

**Prevention:**
- Use the `feature` field (SAE dictionary index, already preserved in `fetch_attribution_subgraph`) as the join key when diffing graphs.
- For nodes without a feature index (logit output nodes, embedding nodes), use the verbalized token string as the join key.
- Define `diff_graphs(control: CompiledGraph, test: CompiledGraph) -> DiffGraph` as a pure function with explicit alignment logic, covered by unit tests with known inputs.
- Treat unmatched nodes (present in one graph, absent in the other) as explicitly meaningful — they are the signal.

**Detection:** In a test where control and test use the same prompt (no knowledge injection), the diff should be empty. If it isn't, alignment is broken.

**Phase:** Core of the differential graph implementation milestone. Get alignment semantics right before building the visualization layer.

---

### Pitfall 4: Streamlit removal breaks the experiment engine's only test surface

**What goes wrong:** The Streamlit pages (`pages/1_Canon_Ball.py`, `pages/2_Borges_Graph.py`) are not just dead UI — they are the only existing exercise of `canon_experiment.py` and `borges_graph.py` with real API calls. Removing them without first establishing an equivalent test surface (even just a CLI script or a `pytest` integration test) removes the only way to catch regressions in the core libraries.

**Why it happens:** When removing legacy code, the instinct is to delete everything that references the old stack. But "legacy UI" ≠ "dead logic." The Streamlit pages imported and exercised the library functions with real parameters.

**Consequences:** A regression in `assemble_messages`, `compile_attribution`, or `_normalize_projection` goes undetected until a researcher notices wrong results. The FastAPI router wraps these functions but doesn't expose a clear exercise path for unit testing.

**Prevention:**
- Before deleting any Streamlit file, audit what library functions it calls with what arguments. Document this as the test surface to replace.
- Create `tests/integration/test_experiment_engine.py` that fires a minimal experiment (2 trials, short prompt) against the real API before removing Streamlit.
- Delete Streamlit files only after the integration test passes.
- Keep `requirements.txt` locked at the versions Streamlit was using until the new test surface is green.

**Detection:** After deletion, can you trigger a full experiment-to-analysis-to-attribution cycle from a non-browser interface? If not, the safety net is gone.

**Phase:** Streamlit removal milestone. Do not delete before test coverage exists for the library layer.

---

## Moderate Pitfalls

---

### Pitfall 5: Backend detection race condition surfaces under deployment

**What goes wrong:** `_get_backend()` in `canon_experiment.py` does a lazy Ollama health probe (1.5s timeout) on the first call. On cloud deployments (Railway, Render, Fly), there is no Ollama, so every cold start wastes 1.5s. Worse: if the warmup endpoint resolves before `CANON_BACKEND` is read from environment, concurrent requests during the warmup window may each independently trigger the probe.

**Why it happens:** Lazy detection is convenient for local dev. It was never replaced with an explicit startup assertion because it "just works" when the .env is set.

**Prevention:**
- Add an assertion in `backend/main.py` lifespan startup: `assert os.getenv("CANON_BACKEND") in ("cloud", "ollama"), "CANON_BACKEND must be set explicitly"`. Fail fast at boot, not at first request.
- Document `CANON_BACKEND=cloud` as required in `.env.example` and deployment config.

**Detection:** Deploy to a cloud environment without `CANON_BACKEND` set. First experiment fires slowly or fails.

**Phase:** Published tool readiness / deployment stabilization.

---

### Pitfall 6: Neuronpedia 429/503 consumed silently, experiment appears to succeed

**What goes wrong:** When Circuit Tracer GPU queue is full (503) or rate limit is hit (429), `neuronpedia_client.py` catches the exception and falls through to the graceful degradation path. The chain state is marked complete. The UI renders placeholder "attribution unavailable" nodes. The researcher believes the chain ran but was uninformative — when in fact it never ran.

**Why it happens:** Graceful degradation for unavailable attribution is the right behavior in production. But "degraded" and "failed silently" look identical to the researcher. The client has no explicit 429 handling with exponential backoff.

**Prevention:**
- Distinguish `status: "degraded_rate_limit"` from `status: "degraded_circuit_error"` in chain state. Surface to UI as "Neuronpedia quota exhausted — retry in Xm" vs. "Attribution unavailable."
- Add explicit 429 detection with `Retry-After` header parsing before falling back.
- Add a pre-flight quota check: if fewer than 12 Circuit Tracer requests remain this hour, warn before firing.

**Detection:** Exhaust the 30/hr quota intentionally. Does the UI distinguish this from a successful-but-empty chain?

**Phase:** Chain stabilization / published tool readiness.

---

### Pitfall 7: Concurrent experiment fires corrupt shared chain state

**What goes wrong:** `chain_state` and `experiment_results` are dicts updated by daemon threads. If two `/api/experiment/fire` calls arrive within seconds (e.g., a researcher double-clicks, or a browser retry fires), the second fire's chain computation will overwrite keys being read by the first fire's daemon. State ends with a mix of results from two different experiments.

**Why it happens:** The current lock strategy (`_state_lock`, `_results_lock`) protects individual dict operations but does not prevent two concurrent experiment lifecycles from running simultaneously.

**Prevention:**
- Add a mutex at the experiment level: if an experiment is already `in_progress`, reject the second fire with `409 Conflict` and a clear message.
- Alternatively, generate a unique `experiment_id` per fire and namespace all state under that ID — concurrency then produces isolated state, not corruption.

**Detection:** Fire two experiments in rapid succession (e.g., via `curl` in parallel). Check whether results mix.

**Phase:** Chain state / backend stabilization.

---

### Pitfall 8: NLA batch position gaps produce shifted verbalizations

**What goes wrong:** `neuronpedia_client.py` batches NLA explain calls by token position (max 16 per request). Results are merged into a dict keyed by position. If a batch returns positions out-of-order or skips a position, the merge is silent. The Focal Line and differential graph display verbalization for position N when the data is actually from position N+1.

**Why it happens:** No assertion on position uniqueness or continuity. The batching logic assumes Neuronpedia returns positions in the same order they were requested.

**Prevention:**
- After merging all batches, assert `sorted(result.keys()) == list(range(min_pos, max_pos + 1))`. Log any gaps.
- In the differential graph specifically, position alignment between control and test NLA results must be validated before rendering — different prompts may have different token counts.

**Detection:** Inject a mock NLA response with a missing position. Does the merge detect the gap or silently shift?

**Phase:** Chain stabilization / differential graph implementation.

---

## Minor Pitfalls

---

### Pitfall 9: UMAP Numba cold-start misread as experiment failure

**What goes wrong:** First experiment after server start takes ~4-6 seconds longer than subsequent ones due to Numba JIT compilation. Researchers who fire immediately after deploying see a slow response and assume the experiment failed, then fire again — producing duplicate work and consuming API quota.

**Prevention:** The warmup endpoint in `backend/main.py` already exists. Ensure it completes before the health check passes. Add a `"warming_up"` status that the frontend polls before enabling the fire button.

**Phase:** Published tool readiness.

---

### Pitfall 10: Sliding window word-count approximation causes context truncation in long knowledge layers

**What goes wrong:** `borges_graph.py`'s `_sliding_window` estimates token count by splitting on whitespace. A knowledge layer with dense text (many punctuation marks, code snippets, or French prose) will be undercounted. The actual prompt sent to Circuit Tracer exceeds the 64-token cap, and Neuronpedia truncates or rejects it without a clear error.

**Prevention:** Use a character-count heuristic (4 chars ≈ 1 token) as a conservative upper bound alongside the word count, and take the maximum. Better: add an explicit `len(prompt) / 4 < 60` guard before calling Circuit Tracer, and surface "knowledge layer too long for attribution" explicitly.

**Phase:** Chain stabilization — low urgency unless researchers use long knowledge layers.

---

### Pitfall 11: fastembed cold-start downloads model during first experiment

**What goes wrong:** If `bge-m3` is not pre-loaded, the first embedding call downloads ~100MB. In a deployment without preloading, this causes the first experiment to time out from the client's perspective (30s+ download + JIT compile + experiment). The client retries, consuming quota.

**Prevention:** The warmup endpoint must download and load the model. Add a Docker `RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-m3')"` step in the build stage so the model is baked into the image.

**Phase:** Published tool readiness / deployment config.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Differential graph implementation | Node alignment by position instead of feature identity (P3) | Define `diff_graphs()` pure function with feature-key join before building UI |
| Differential graph implementation | Rendering stale chains from previous experiment (P1) | Implement chain invalidation before or alongside diff view |
| Differential graph implementation | `"?"` token labels making alignment meaningless (P2) | Add schema assertion + unit test for token extraction first |
| Streamlit removal | Losing the only exercise path for core libraries (P4) | Write integration tests before deleting any Streamlit file |
| Chain stabilization | Concurrent fires corrupting shared state (P7) | Add experiment-level mutex (409 on concurrent fire) |
| Chain stabilization | Silent 429/503 misread as empty attribution (P6) | Add explicit status distinction + pre-flight quota check |
| Chain stabilization | NLA position gaps shifting verbalizations (P8) | Add post-merge position continuity assertion |
| Backend detection fix | Race at cold start under deployment (P5) | Assert `CANON_BACKEND` at lifespan startup, fail fast |
| Published tool readiness | UMAP cold-start misread as failure (P9) | Ensure warmup blocks health check |
| Published tool readiness | fastembed download on first experiment (P11) | Bake model into Docker image |

---

## Sources

- Project codebase analysis: `.planning/codebase/CONCERNS.md` (HIGH confidence — direct code evidence)
- FastAPI background task failure modes: [FastAPI Background Task Failure (DrDroid)](https://drdroid.io/framework-diagnosis-knowledge/fast-api-background-task-failure), [Pitfalls of Async Task Management in FastAPI (Leapcell)](https://leapcell.io/blog/understanding-pitfalls-of-async-task-management-in-fastapi-requests) (MEDIUM confidence)
- Attribution graph interpretability limitations: [Pitfalls in Evaluating Interpretability Agents (arXiv)](https://arxiv.org/pdf/2603.20101), [Circuit Tracing and Attribution Graphs (LearnMechInterp)](https://learnmechinterp.com/topics/circuit-tracing/) (MEDIUM confidence)
- Neuronpedia Circuit Tracer blog: [Circuit Tracer + New Auto-Interp Method (Neuronpedia)](https://www.neuronpedia.org/blog/circuit-tracer) (MEDIUM confidence)
- API 429 silent failure patterns: [How to handle API rate limits (DEV Community)](https://dev.to/robertobutti/how-to-handle-api-rate-limits-and-http-429-errors-in-an-easy-and-reliable-way-14e6) (MEDIUM confidence)
- Brownfield migration pitfalls: [The Hardest Lesson I Learned Migrating Legacy Code (canro91)](https://canro91.github.io/2025/09/18/LegacyMigration/) (LOW confidence — general, not interpretability-specific)
