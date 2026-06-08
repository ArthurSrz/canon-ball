# Project Research Summary

**Project:** Canon Ball
**Domain:** LLM interpretability experiment instrument (attribution graph differential visualization + research tool hardening)
**Researched:** 2026-06-08
**Confidence:** HIGH

## Executive Summary

Canon Ball is an already-functional interpretability instrument with a clear gap: the differential Borges graph. The statistical half of the tool (semantic dispersion, UMAP, Mann-Whitney U) is complete and correct. The mechanistic half (WHY dispersion reduces) is partially built — single-chain attribution via Circuit Tracer and Focal Line are in place — but the control-vs-test attribution diff that would close the research question does not exist yet. This is not a greenfield build; every component the diff feature needs (two CompiledGraph objects on disk, an existing SVG renderer, RawBlock color vocabulary, and a 6-step rail navigation shell) is already present. The milestone is building the diff computation layer and a new visualization screen on top of what exists.

The recommended approach is strictly additive: one new backend endpoint (GET /api/chain/diff), one new API wrapper, one new React component (DiffBorgesGraph), and one new screen (DiffScreen, step 06). No new libraries. No new backend models. No new API integrations. The diff is pure Python set/dict algebra over data already on disk. The visualization is inline SVG following the exact pattern of the existing BorgesGraph component. After the diff ships, the secondary work is stabilizing the chain pipeline (state invalidation, concurrent fire protection, 429 handling) and preparing the tool for public exposure (rate limiting, CANON_BACKEND assertion, warmup correctness).

The principal risk is data integrity, not engineering complexity. Three pitfalls can produce silently wrong research results: rendering stale chains from a previous experiment (chain invalidation not implemented), aligning attribution graph nodes by position instead of SAE feature identity (produces meaningless diffs), and accepting "?" token labels from a broken Circuit Tracer regex without surfacing the failure. All three must be addressed before the differential graph ships, because a diff built on wrong data is worse than no diff.

## Key Findings

### Recommended Stack

No new dependencies are required for the core differential graph feature. The frontend is pure React 18.3.1 + inline SVG, which is already the pattern used everywhere in the codebase. The 40-node cap in borges_graph.py makes any argument for Canvas, WebGL, or a graph library (React Flow, Cytoscape, D3) irrelevant — the scale is too small to matter and the fixed coordinate system (depth x ctx_idx axes) is semantically meaningful, not aesthetic. CSS transitions handle all animation needs.

For published tool readiness, one new Python dependency is justified: slowapi>=0.1.9 for rate limiting on /api/experiment/fire, which calls OpenRouter per trial and must not be exposed without a token bucket.

**Core technologies:**
- React 18.3.1 + inline SVG: differential graph visualization — only correct choice given existing codebase and fixed-coordinate layout
- Vite ^6.0.0: build + dev server — already configured, no changes needed
- FastAPI + existing routers: diff endpoint — pure Python computation, no new library
- slowapi ^0.1.9: rate limiting — required before public deployment, not before diff feature works
- nixpacks + Procfile: deployment — already configured for Python 3.13 + Node 20 multi-stage build

### Expected Features

The codebase is already past MVP for the statistical/semantic instrument. The features gap is narrow and specific.

**Must have (table stakes):**
- Differential Borges graph (control vs test side-by-side/overlay) — the core research question is unanswered without it; no other tool provides this view
- Chain state invalidation — differential view is actively misleading without this; stale chains are the worst failure mode
- Error messaging for chain failures — researchers currently cannot distinguish "attribution unavailable" from "Neuronpedia quota exhausted"

**Should have (differentiators already built, need polish):**
- Injection mode as first-class experimental variable — already built; most tools treat prompt structure as fixed
- Focal Line convergence visualization — already built; unusual in the ecosystem
- RawBlock semantic color encoding — already built; control=black / test=red / knowledge=orange is consistent across all screens

**Defer (v2+):**
- Streamlit removal — zero researcher-facing impact; do after diff ships
- Published tool readiness (CORS lock, rate limiting, warmup) — necessary before sharing publicly, not before core feature works
- SAE feature steering UI — feature IDs are preserved in CompiledGraph for future use; building a steering interface is a different product

### Architecture Approach

The differential graph integrates as step 06 in the existing 6-step rail. Both chains are already serialized to disk by the existing background thread — no new computation is required. The diff endpoint reads chain_control.json and chain_test.json, computes node-level deltas (delta_influence, status: added/removed/amplified/suppressed/unchanged), caches the result to chain_diff.json, and serves it. The frontend polls chain status, fetches the diff payload, and renders it via a new DiffBorgesGraph component that follows the existing BorgesGraph SVG pattern exactly.

**Major components:**
1. GET /api/chain/diff (new backend route) — reads both chain files from disk, computes diff, caches to chain_diff.json; node identity key is SAE feature index (not position)
2. DiffBorgesGraph.jsx (new component) — inline SVG; accepts diffSteps array; side-by-side or overlay view mode; delta encoded in RawBlock colors; step scrubber shared between both chains
3. DiffScreen.jsx (new screen, step 06) — polls chain status, fetches diff, mounts DiffBorgesGraph; follows FocalLineScreen pattern exactly
4. Chain invalidation fix (prerequisite) — resets _chain_state and deletes all three chain JSON files on new experiment fire; adds chain_experiment_id guard in diff view

### Critical Pitfalls

1. **Stale chain rendering** — chain state is not invalidated when a new experiment fires; the diff view will show results from the previous experiment silently. Fix: atomically reset chain state to {"status": "invalidated"} as the first operation in /api/experiment/fire, add chain_experiment_id field, refuse to render diff if IDs do not match.

2. **Node alignment by position, not identity** — looping over two node lists in parallel produces nonsense diffs because knowledge injection changes circuit topology; positional alignment is the canonical mistake in attribution diffing. Fix: use feature (SAE dictionary index, already preserved in CompiledGraph) as join key; for embedding/logit nodes without a feature index, use verbalized token string.

3. **Silent "?" token labels** — the Circuit Tracer label regex has a permissive fallback that produces "?" without surfacing the failure; diff alignment built on "?" labels is meaningless. Fix: add schema assertion on raw Circuit Tracer response; replace "?" fallback with None and propagate visibly; add a unit test for _extract_token_label.

4. **Streamlit removal loses only test surface** — the Streamlit pages are the only existing exercise path for canon_experiment.py and borges_graph.py with real API calls; deleting them without replacement removes the only regression detection. Fix: write tests/integration/test_experiment_engine.py before deleting any Streamlit file.

5. **Silent 429/503 misread as empty attribution** — graceful degradation makes "quota exhausted" and "successful but empty chain" indistinguishable to the researcher. Fix: add explicit status "degraded_rate_limit" vs "degraded_circuit_error" distinction; surface as readable UI message.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Chain Data Integrity (Prerequisites)
**Rationale:** The differential graph is worse than useless if built on stale or misaligned data. Three correctness prerequisites must land before any visualization work starts: chain state invalidation, token label schema assertion, and the diff_graphs() pure function with feature-key alignment. These are small, targeted, and unblock everything downstream.
**Delivers:** A chain pipeline that can be trusted; a diff_graphs() function with unit tests that defines the alignment contract
**Addresses:** Chain state invalidation, token label extraction correctness
**Avoids:** Pitfalls 1, 2, 3 (stale chains, positional alignment, silent "?" labels)

### Phase 2: Differential Borges Graph
**Rationale:** Once data integrity is guaranteed, the differential graph is the single highest-value feature — it completes the WHY instrument and makes the chain-centric design pay off. Build order within this phase follows strict dependency: backend diff endpoint first (defines payload shape), then API wrapper, then DiffBorgesGraph component (can be developed with mock data), then DiffScreen as the orchestrating shell.
**Delivers:** Step 06 in the rail; side-by-side and overlay views; step scrubber synced between control and test chains; delta encoding in RawBlock colors
**Uses:** React inline SVG, existing BorgesGraph pattern, RawBlock CSS vars, diff payload from Phase 1 endpoint
**Implements:** DiffScreen, DiffBorgesGraph, getDiff() API wrapper, GET /api/chain/diff
**Avoids:** Pitfall of adding a graph library; anti-pattern of re-requesting Neuronpedia for diff computation

### Phase 3: Chain Pipeline Stabilization
**Rationale:** With the differential graph shipping, the chain pipeline becomes load-bearing for the primary research workflow. Three backend hardening items that were acceptable to defer become necessary: concurrent fire protection, NLA position validation, and 429/503 status distinction.
**Delivers:** A chain pipeline that handles edge cases correctly without silent failures
**Addresses:** Concurrent experiment fires (409 mutex), NLA batch position gaps, Neuronpedia quota surfacing
**Avoids:** Pitfalls 5, 6, 7, 8 (backend detection race, silent 429, concurrent corruption, NLA position gaps)

### Phase 4: Streamlit Removal
**Rationale:** Deferred until after Phase 3 because it has zero researcher-facing impact, requires an integration test surface to replace the only existing exercise path for core libraries, and with the diff feature shipped, the FastAPI routers are the actual exercise path.
**Delivers:** Clean codebase without legacy Streamlit pages; integration test suite for core libraries
**Avoids:** Pitfall 4 (losing only test surface during removal)

### Phase 5: Published Tool Readiness
**Rationale:** Rate limiting, CANON_BACKEND startup assertion, UMAP warmup correctness, and fastembed model pre-baking are only needed before public exposure. They are pure deployment concerns with no impact on research functionality.
**Delivers:** Public deployment with rate limiting, correct cold-start behavior, no UMAP/fastembed surprise latency
**Uses:** slowapi ^0.1.9, nixpacks Dockerfile warmup step
**Avoids:** Pitfalls 5, 9, 11 (backend detection race, UMAP cold-start, fastembed download on first experiment)

### Phase Ordering Rationale

- Phase 1 before Phase 2: data integrity is a correctness prerequisite, not an enhancement; building visualization on unvalidated alignment logic produces wrong research results
- Phase 2 before Phase 3: chain stabilization adds resilience to a working feature; doing it first is premature optimization
- Phase 4 after Phase 3: integration tests can only be written once the FastAPI routers are the authoritative exercise path; that is true after the chain pipeline is stable
- Phase 5 last: deployment hardening is only relevant when sharing publicly; doing it earlier blocks nothing

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** Chain invalidation and schema assertions are standard backend patterns; no novel API surface
- **Phase 2:** Diff visualization follows established existing component pattern; payload shape is fully specified in ARCHITECTURE.md
- **Phase 3:** FastAPI concurrency mutex (409 pattern) and retry-after handling are documented patterns
- **Phase 4:** Integration test creation and Streamlit removal are mechanical; no research needed
- **Phase 5:** slowapi integration is well-documented; nixpacks warmup is configuration-level work

No phases require a research-phase run. All patterns are well-specified by the existing codebase and research files.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified directly from package.json, existing component implementations, and borges_graph.py node caps |
| Features | MEDIUM | Table stakes from ecosystem survey (Neuronpedia, Anthropic attribution-graphs-frontend); differentiator assessment from first principles |
| Architecture | HIGH | Based on direct codebase analysis; payload shapes derived from actual dataclass definitions |
| Pitfalls | HIGH | All pitfalls grounded in codebase evidence from CONCERNS.md + domain verification |

**Overall confidence:** HIGH

### Gaps to Address

- **slowapi version:** STACK.md flags that 0.1.9 should be confirmed with pip index versions slowapi before pinning — verify during Phase 5
- **Overlay coordinate normalization:** The exact normalization for shared axes in overlay mode (using Math.max(maxDepth_ctrl, maxDepth_test)) may need adjustment if chains have significantly different depths — validate empirically during Phase 2
- **Null-feature node join key:** SAE feature index is the primary join key, but embedding and logit nodes have feature: null; the fallback to verbalized token string needs empirical validation on real chain data — validate during Phase 1 when writing diff_graphs() unit tests

## Sources

### Primary (HIGH confidence)
- Existing codebase: borges_graph.py, backend/routers/chain.py, frontend/src/screens/FocalLineScreen.jsx, frontend/package.json, .planning/codebase/CONCERNS.md
- https://www.anthropic.com/research/open-source-circuit-tracing — Anthropic circuit tracing open source release
- https://github.com/anthropics/attribution-graphs-frontend — Anthropic attribution graphs frontend source
- https://transformer-circuits.pub/2025/attribution-graphs/methods.html — Circuit Tracing methodology paper
- https://github.com/hijohnnylin/neuronpedia — Neuronpedia open source platform

### Secondary (MEDIUM confidence)
- https://www.neuronpedia.org/graph/info — Circuits research landscape
- https://fredhohman.com/summit/ — Summit: Scaling Deep Learning Interpretability
- FastAPI background task failure mode documentation
- https://www.neuronpedia.org/blog/circuit-tracer — Circuit Tracer + NLA blog

### Tertiary (LOW confidence)
- Differential graph comparison as open research opportunity — ecosystem inference from Summit (2019) + 2026 landscape survey; not yet standard in LLM interpretability tools
- Brownfield migration pitfalls — general software engineering patterns, not interpretability-specific

---
*Research completed: 2026-06-08*
*Ready for roadmap: yes*
