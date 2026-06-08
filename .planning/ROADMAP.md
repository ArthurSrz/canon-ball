# Roadmap: Canon Ball

## Overview

Canon Ball is a brownfield project with a narrow, well-defined gap. The experiment engine, semantic analysis, and single-chain attribution are all operational. The milestone is closing the research question: building the differential Borges graph (WHY did knowledge change the model's outputs), stabilizing the pipeline behind it, and clearing the legacy Streamlit dead weight. Three phases derived directly from the requirement categories, in strict correctness-before-visualization order.

## Phases

- [ ] **Phase 1: Chain Data Integrity** - Fix chain invalidation, SAE-key diff alignment, and token label schema — prerequisites for a trustworthy diff
- [ ] **Phase 2: Differential Borges Graph** - Backend diff endpoint + DiffBorgesGraph component + DiffScreen as step 06 in the rail
- [ ] **Phase 3: Cleanup and Deployment Readiness** - Streamlit removal, CANON_BACKEND startup assertion, CORS lockdown

## Phase Details

### Phase 1: Chain Data Integrity
**Goal**: The chain pipeline produces correct, current data that can be safely used to build a diff
**Depends on**: Nothing (first phase)
**Requirements**: INTG-01, INTG-02, INTG-03
**Success Criteria** (what must be TRUE):
  1. Firing a new experiment immediately invalidates prior chain files; a stale diff cannot be served
  2. diff_graphs() joins nodes by SAE feature key (feature, depth, ctx_idx), not list position; a unit test verifies alignment on two distinct graphs
  3. A malformed or missing Circuit Tracer label raises a structured error rather than silently substituting "?"
**Plans**: TBD

### Phase 2: Differential Borges Graph
**Goal**: Researchers can compare control and test attribution chains side-by-side at step 06 in the rail
**Depends on**: Phase 1
**Requirements**: DIFF-01, DIFF-02, DIFF-03, DIFF-04
**Success Criteria** (what must be TRUE):
  1. GET /api/chain/diff returns a delta-encoded payload with per-node status (added, removed, amplified, suppressed, unchanged) and delta_influence values once both chains are ready
  2. DiffBorgesGraph renders knowledge-added nodes in orange, suppressed nodes in red, and shared/unchanged nodes in grey, using the existing RawBlock palette
  3. DiffScreen appears as step 06 in the 6-step rail and polls chain status before rendering; a researcher can scrub through both chains in sync
**Plans**: TBD
**UI hint**: yes

### Phase 3: Cleanup and Deployment Readiness
**Goal**: The codebase contains no dead Streamlit weight and is safe to expose publicly
**Depends on**: Phase 2
**Requirements**: CLEN-01, CLEN-02, CLEN-03
**Success Criteria** (what must be TRUE):
  1. app.py, pages/, shared_sidebar.py, html_components.py are deleted; no import in the active codebase references them
  2. The FastAPI process asserts CANON_BACKEND at startup; the 1.5s Ollama probe on first request does not occur
  3. allow_origins is restricted to an explicit domain list via ALLOWED_ORIGINS; a wildcard origin is rejected
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Chain Data Integrity | 0/? | Not started | - |
| 2. Differential Borges Graph | 0/? | Not started | - |
| 3. Cleanup and Deployment Readiness | 0/? | Not started | - |
