# Technology Stack — Differential Borges Graph & Interpretability Dashboard

**Project:** Canon Ball
**Feature scope:** Differential Borges graph (control vs test attribution comparison) + Streamlit removal + published tool readiness
**Researched:** 2026-06-08
**Overall confidence:** HIGH for graph rendering decision; MEDIUM for supporting library versions

---

## Core Decision: No New Graph Library

The existing `FocalLineScreen.jsx` already implements a bespoke SVG graph renderer (pure React + inline SVG, ~130 lines). Nodes carry `depth`, `ctx_idx`, `influence`, `type`, and `label` from the `CompiledGraph` dataclass. The differential view is an additive extension of this renderer — not a new dependency.

**Do NOT introduce** React Flow, Cytoscape.js, D3, or react-force-graph for the differential Borges graph. The graph structure (depth × ctx_idx scatter with sized circles) is a fixed domain-specific layout, not a general flowchart or force simulation. Adding a third-party graph library would:
- Import 200 KB+ of layout machinery that the fixed-coordinate system doesn't use
- Break the RawBlock design system (these libraries ship their own DOM structure and default styles)
- Add a migration burden with no payoff — the existing SVG is already composable, stateless, and idiomatic React

The right path for differential rendering is a new `DifferentialBorgesGraph` component that accepts `control` and `test` graphs and renders delta-encoding inline: shared nodes in grey, test-only activations in orange (var(--gold)), control-only suppressions in red (var(--test)), with influence-scaled circle sizes.

---

## Recommended Stack

### Graph / Visualization Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React inline SVG | (built-in) | Differential Borges graph, Focal Line, Semantic Map | Already used everywhere; zero-cost interop with RawBlock CSS vars; SVG viewBox scales perfectly; dom inspection via browser devtools; no build-time overhead |
| No graph library | — | — | Attribution graph has ~40 nodes max (capped in `fetch_attribution_subgraph`); fixed coordinate system; no force layout needed; performance is irrelevant at this scale |

**Confidence: HIGH.** Verified by reading existing implementation. The 40-node / 200-link cap in `borges_graph.py` makes performance arguments for Canvas or WebGL completely moot.

### Animation / Transition (optional, differential highlight)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| CSS transitions | (built-in) | Fade in delta nodes, highlight activated paths | Already used in the progress bar (`transition: width 0.5s ease`); zero cost; sufficient for opacity and fill transitions on SVG elements |

Do not use Framer Motion or GSAP. The animations needed are SVG `opacity` and `fill` transitions that CSS handles natively.

### Semantic Map (existing — no changes needed)

The UMAP scatter plot (`SemanticMap.jsx`) is already implemented. No library recommendation needed — verify it uses the same inline SVG pattern before touching it.

### Frontend Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.3.1 | UI layer | Already in use; stay on 18.x — do NOT upgrade to 19 during this feature work (React 19 changed `ref` handling and concurrent behavior; upgrade is a separate task) |
| Vite | ^6.0.0 | Build + dev server | Already configured with API proxy to port 8000; no changes needed |

**Confidence: HIGH.** Verified from `package.json`.

### Backend (FastAPI)

No new dependencies needed for the differential graph feature. The backend already:
- Computes two chains (control + test) in a background thread
- Serializes both via `CompiledGraph.to_dict()`
- Exposes them at `GET /api/chain/results`

The differential comparison logic (node matching, delta encoding) belongs in the **frontend**, not the backend. The two graph payloads are already available; merging them for display is a pure UI concern. Do not add a new `/api/chain/diff` endpoint — it would serialize what the frontend can compute in microseconds from data already in memory.

**Confidence: HIGH.**

### State Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React useState / useMemo | (built-in) | Differential node matching, step sync between graphs | The existing BorgesGraph component uses useMemo for cluster computation; the differential component needs the same pattern — compute delta nodes once from props, memoize |

Do not introduce Zustand, Redux, or Jotai. The app is a single-session linear rail (6 steps). Global state is props-drilled experiment data. This is correct for the scale and session model.

### Deployment / Infrastructure (published tool readiness)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| nixpacks | (existing) | Container build | Already configured in `nixpacks.toml`; handles Python 3.13 + Node 20 multi-stage build |
| Procfile | (existing) | Process declaration | Already present for Heroku/Railway/Render |
| slowapi | ^0.1.9 | Rate limiting on experiment endpoints | Wraps FastAPI with Redis-optional token bucket; use in-memory store for single-instance deploy; needed before public exposure of `/api/experiment/fire` which calls OpenRouter per trial |
| python-dotenv | ^1.0.0 | Env loading in production | Already used implicitly via `backend/config.py`; make explicit for nixpacks clarity |

**Confidence: MEDIUM for slowapi** — verified it is the standard FastAPI rate limiting library (analogous to Flask-Limiter), but version 0.1.9 is from training data and should be confirmed with `pip index versions slowapi` before pinning.

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Graph rendering | Pure React SVG | React Flow (@xyflow/react ^12.x) | React Flow is for user-editable node diagrams; our layout is computed (fixed coordinate axes); adds ~250 KB for no gain; breaks RawBlock CSS |
| Graph rendering | Pure React SVG | Cytoscape.js + react-cytoscapejs | Excellent for large force-directed graphs (thousands of nodes); overkill for 40-node fixed scatter; canvas rendering breaks SVG-native hover/tooltip pattern already in use |
| Graph rendering | Pure React SVG | D3.js | D3 DOM mutations conflict with React's virtual DOM; the standard workaround (D3 for math, React for rendering) is exactly what the existing code already does manually — without the D3 dependency |
| Graph rendering | Pure React SVG | react-force-graph | Force-directed layout (physics simulation) is the wrong mental model for attribution graphs — node positions encode layer depth and context position, which are meaningful coordinates, not aesthetic ones |
| Animation | CSS transitions | Framer Motion | 40 KB gzipped; the transitions needed (opacity, fill) are two CSS properties; not worth the dependency |
| State | useState/useMemo | Zustand | Single-session tool; no cross-component reactive state; adding a store adds complexity with no payoff |

---

## Installation

For the differential Borges graph and Streamlit removal, no new npm packages are needed. The frontend changes are pure React + SVG.

For published tool readiness (rate limiting):

```bash
# Python — add to requirements.txt
pip install slowapi>=0.1.9
```

No new npm packages required.

---

## What the Differential Graph Component Needs (design spec for implementation)

The `DifferentialBorgesGraph` component receives `{ control: CompiledGraph, test: CompiledGraph }` and produces an overlaid or side-by-side SVG. Node matching uses `(depth, ctx_idx, type)` as identity key. Delta categories:

- **Shared node, similar influence** → grey (#ccc), small
- **Shared node, test influence > control** → orange (var(--gold)), sized by delta
- **Test-only node** → orange filled, dashed border
- **Control-only node (suppressed by KL)** → red (var(--test)), hollow with solid border

This encoding directly answers the research question — "what did this knowledge layer activate?" — without requiring a new library or a new API endpoint.

---

## Sources

- Existing codebase: `frontend/src/screens/FocalLineScreen.jsx`, `frontend/package.json`, `borges_graph.py`
- [React Flow (@xyflow/react) — latest v12.11.0](https://www.npmjs.com/package/@xyflow/react) — rejected
- [Cytoscape.js React integration](https://github.com/plotly/react-cytoscapejs) — rejected
- [react-force-graph — vasturiano](https://github.com/vasturiano/react-force-graph) — rejected
- [SVG vs Canvas performance at scale](https://blog.logrocket.com/best-react-chart-libraries-2026/) — scale arguments irrelevant at 40-node cap
- [Neuronpedia open source](https://github.com/hijohnnylin/neuronpedia) — uses Next.js + their own graph viewer, not applicable here
