# Canon Ball

## What This Is

An interpretability instrument for researchers studying what knowledge does to language models. Researchers configure a prompt and a knowledge layer (system prompt), fire paired experiments (control: LLM without knowledge / test: LLM with knowledge), and read two complementary answers: Canon Ball's semantic dispersion metrics (the WHAT) and a differential Borges graph comparing attribution chains (the WHY — which tokens the knowledge activated).

## Core Value

A researcher can fire one experiment and get a direct, visual answer to "what did this knowledge layer do to this model's output distribution?"

## Requirements

### Validated

*(Inferred from existing codebase — shipped and operational)*

- ✓ **Experiment engine**: Fire N control + N test trials via OpenRouter (gemma-3-4b-it), embed via fastembed — existing
- ✓ **Injection modes**: Four strategies for knowledge injection (system_user, interleave, template, cot_priming) — existing
- ✓ **Semantic analysis**: UMAP projection, dispersion metrics (euclidean/cosine), Mann-Whitney U test — existing
- ✓ **Attribution chain (Borges graph)**: Circuit Tracer via Neuronpedia, NLA verbalization, CompiledGraph dataclass — existing
- ✓ **Focal Line scene**: Attribution subgraph + NLA verbalizations mapped to SVG visualization — existing
- ✓ **React frontend**: 6-step rail (Concept → Setup → Map → Metrics → Modes → Focal Line) — existing
- ✓ **FastAPI backend**: REST API, background chain computation, disk persistence — existing

### Active

- [ ] **Differential Borges graph**: Side-by-side or overlaid attribution graphs (control vs test), highlighting tokens the knowledge layer activated or suppressed
- [ ] **Streamlit removal**: Remove legacy `app.py`, `pages/`, `shared_sidebar.py`, `html_components.py` (1,139 lines of dead weight)
- [ ] **Chain state invalidation**: Reset chain state on new experiment fire; recover from "stuck computing" state without server restart
- [ ] **Backend detection fix**: Set explicit `CANON_BACKEND` at startup rather than lazy probe; eliminate 1.5s block on first call
- [ ] **Published tool readiness**: CORS locked to explicit domain, rate limiting on experiment endpoints, deployment config (nixpacks/Procfile already present)

### Out of Scope

- Fine-tuning or weight modification — knowledge is injection-time only (system prompt layer)
- Persistent experiment history / comparison across runs — v1 is single-session, configure+fire+read
- Multi-model comparison — single model (gemma-3-4b-it) for trials; attribution uses gemma-2-2b
- Authentication / user accounts — not needed for published research tool without persistence

## Context

**Existing codebase is brownfield mid-migration.** FastAPI + React is the active stack; Streamlit is legacy and should be removed. The core experiment engine (`canon_experiment.py`), analysis (`canon_analysis.py`), attribution graph builder (`borges_graph.py`), and Neuronpedia client (`neuronpedia_client.py`) are all functional as standalone libraries — the React/FastAPI layer wraps them.

**Two-chain architecture already implemented:** Background thread computes control chain + test chain after each experiment. The pieces for differential comparison exist; they're not yet exposed as a unified diff view.

**Rate limits to respect:** Circuit Tracer 30 requests/hour; NLA explain caps at 16 token positions per request (auto-batched). Neuronpedia model: gemma-2-2b (Circuit Tracer), gemma-3-27b-it layer 41 (NLA).

**Design system:** RawBlock brutalist — white ground, black borders, control=black, test=red, knowledge=orange. Already implemented in `frontend/src/styles.css`.

## Constraints

- **Tech stack**: FastAPI + React/Vite — no switching mid-flight
- **Models**: gemma-3-4b-it (OpenRouter) for trials; gemma-2-2b (Neuronpedia) for attribution — API-locked
- **Rate limits**: Circuit Tracer 30/hr hard cap; NLA 16-position batch cap
- **Knowledge form**: System prompt layer only (not RAG, not fine-tuning)
- **Scope**: Configure + fire + read results in a single session (no persistence)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Chain-centric design (Borges chain as central artifact) | Attribution chain explains WHY dispersion changes, not just WHAT | — Pending |
| Two chains per experiment (not per trial) | Rate limits make per-trial chain computation infeasible | ✓ Good |
| Background thread for chain computation | Chains take seconds; user should see UMAP immediately | ✓ Good |
| Streamlit removal (not maintenance) | Dual code path doubles maintenance burden; React is the canonical UI | — Pending |
| Differential graph as new instrument | Side-by-side attribution comparison directly answers the research question | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-08 after initialization*
