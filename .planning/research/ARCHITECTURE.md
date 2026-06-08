# Architecture Patterns: Differential Borges Graph

**Project:** Canon Ball
**Researched:** 2026-06-08
**Confidence:** HIGH (based on direct codebase analysis)

---

## Recommended Architecture

The differential Borges graph integrates as a new screen (step 06) in the existing 6-step rail, consuming data already on disk. No new background computation is needed — both chains are already built by the existing `start_chains_bg()` thread. The feature gap is purely in the diff computation layer (backend) and the visualization layer (frontend).

```
[chain_control.json]   [chain_test.json]
         \                   /
          v                 v
   GET /api/chain/results  (already exists)
          |
   NEW: GET /api/chain/diff
          |
          v
   DiffBorgesGraph component (new)
   inside new DiffScreen (step 06)
```

---

## Component Boundaries

### Existing Components (unchanged)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `backend/routers/chain.py` | Builds chains in background thread, exposes chain data | `borges_graph.py`, `neuronpedia_client.py`, frontend via HTTP |
| `GET /api/chain/results` | Returns raw `chain_control.json` + `chain_test.json` as `{control, test}` | Frontend `FocalLineScreen` |
| `FocalLineScreen.jsx` | Displays one chain at a time (BorgesGraph component, step scrubber) | `getChainResults()` in `api.js` |
| `BorgesGraph` (inside FocalLineScreen) | SVG render of one CompiledGraph: clusters by (depth, ctx_idx), token scrubber | Props: `graph`, `color`, `label` |

### New Components

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `GET /api/chain/diff` | Computes diff between control and test chains; returns aligned steps with node-level delta | Reads `chain_control.json` + `chain_test.json` from disk |
| `DiffScreen.jsx` (step 06) | Layout shell for side-by-side or overlay view; toggles between modes | `getDiff()` in `api.js`, existing `getChainStatus()` |
| `DiffBorgesGraph.jsx` | SVG: renders control and test graphs aligned by step index, encodes delta with color/size | `diff` payload from `/api/chain/diff` |
| `getDiff()` in `api.js` | HTTP wrapper for new diff endpoint | `DiffScreen` |

---

## Data Flow

### Chain Data Already Available

Both chains are serialized to disk as `CompiledGraph.to_dict()`:

```
{
  "prompt": str,
  "system_prompt": str,          # "" for control, knowledge layer for test
  "model": "gemma-2-2b",
  "generated_text": str,
  "steps": [
    {
      "index": int,
      "token": str,
      "context_length": int,
      "attribution": {...},       # raw Neuronpedia API response
      "subgraph": {
        "ok": bool,
        "nodes": [
          {
            "id": str,
            "type": str,          # "embedding" | "cross layer transcoder" | "logit"
            "depth": int,
            "ctx_idx": int,
            "influence": float,
            "layer": int | null,
            "feature": int | null, # SAE index, preserved for steering
            "label": str
          }
        ],
        "links": [{"source": str, "target": str, "weight": float}]
      }
    }
  ]
}
```

### Diff Computation (new backend logic)

The diff algorithm lives in `GET /api/chain/diff` and operates on the two already-loaded chains:

```
Input:  control CompiledGraph, test CompiledGraph
Output: diff payload

For each step index i (aligned by position):
  ctrl_nodes = {node_id: node} from control.steps[i].subgraph
  test_nodes = {node_id: node} from test.steps[i].subgraph

  For each node_id in union(ctrl_nodes, test_nodes):
    delta_influence = test_influence - ctrl_influence  # positive = knowledge activated
    status = "added" | "removed" | "amplified" | "suppressed" | "unchanged"

  For each link: same delta logic

diff_step = {
  "index": i,
  "ctrl_token": str,
  "test_token": str,
  "token_changed": bool,
  "nodes": [{ ...node_fields, "delta": float, "status": str }],
  "links": [{ ...link_fields, "delta": float }]
}
```

Alignment is by step index. Token divergence (control generates word A, test generates word B at step 3) is surfaced as `token_changed: true` — the visualization marks that step specially. No attempt to realign after divergence: both chains ran independently, step index is the only alignment key.

### Frontend Data Flow

```
DiffScreen mounts
  → getChainStatus() poll until "ready"
  → getDiff() → GET /api/chain/diff
  → diff payload arrives
  → DiffBorgesGraph renders both chains aligned
  → user scrubs step slider
  → delta highlights update per step
```

---

## Patterns to Follow

### Pattern 1: Aligned Step Scrubber

**What:** Single step slider controls both control and test graph simultaneously, advancing through token positions in sync.
**When:** User wants to follow the causal chain token by token.
**Implementation:** Step index is the single source of truth; both graph renders read `diff.steps[i].nodes` filtered by control vs test origin.

### Pattern 2: Delta Encoding with RawBlock Colors

**What:** Node influence delta encoded visually.
**Mapping:**
- `delta > threshold AND status == "added"` → orange (`var(--gold)`) — knowledge activated this feature
- `delta < -threshold AND status == "suppressed"` → gray/faded — knowledge suppressed this feature
- `token_changed: true` → step marker in red (`var(--test)`)
- control baseline → black (`var(--control)`)
- node size proportional to `abs(influence)` (already done in BorgesGraph)

**When:** Every render. This is the primary research signal.

### Pattern 3: Side-by-Side vs Overlay Toggle

**What:** Two render modes — side-by-side (two SVG panels) and overlay (single SVG, control=black, test=red, deltas highlighted).
**When:** Side-by-side for clarity; overlay for comparing paths directly.
**Implementation:** Single `viewMode` prop; both modes consume the same diff payload. Overlay requires shared coordinate normalization across both chains (use `Math.max(maxDepth_ctrl, maxDepth_test)`).

### Pattern 4: Status-based Node Filtering

**What:** Checkboxes or toggle to show only `added`, `amplified`, `suppressed` nodes (hide `unchanged`).
**When:** Dense subgraphs (40 nodes each = up to 80 in overlay) need filtering for legibility.
**Implementation:** Client-side filter on diff payload — no backend call needed.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Re-requesting Neuronpedia for the Diff

**What:** Calling Circuit Tracer again to build the diff.
**Why bad:** 30 requests/hour rate limit. Both chains are already on disk. Any re-computation burns rate limit quota for no gain.
**Instead:** Read `chain_control.json` and `chain_test.json` from disk in the diff endpoint. Pure computation, no external API calls.

### Anti-Pattern 2: Realigning Chains After Token Divergence

**What:** Trying to semantically align chains after they diverge (control → "Paris", test → "France").
**Why bad:** Attribution graphs are context-dependent. After step 3 diverges, the contexts are different — node IDs from step 4 onward may not be comparable. Forced alignment creates misleading diff.
**Instead:** Surface divergence explicitly at the step level (`token_changed: true`). Let the researcher decide if the pre-divergence steps (where the prompt is identical) are the meaningful signal.

### Anti-Pattern 3: New Screen Breaks 6-Step Rail

**What:** Adding DiffScreen as a modal or parallel route instead of step 06 in the rail.
**Why bad:** The rail is the navigation paradigm. Researchers read linearly: Concept → Setup → Map → Metrics → Modes → FocalLine. The diff view is step 06, after FocalLine.
**Instead:** Add step 06 to the `STEPS` array in `App.jsx`. Follow the `FocalLineScreen` pattern exactly.

### Anti-Pattern 4: Diff Computed on Every Poll

**What:** `/api/chain/diff` recomputing the delta on every frontend request.
**Why bad:** Step iteration + set algebra over 40-node subgraphs × 6 steps is cheap, but idempotent for the same experiment. Wasteful if user scrubs frequently.
**Instead:** Compute once per experiment, cache result in `results/chain_diff.json` alongside the other chain files. Invalidate on new experiment fire (same pattern as `chain_control.json`).

---

## Build Order (Dependency Order)

The following is the correct sequence. Each step is unblocked by the previous.

### Step 1: Backend Diff Endpoint

**Files:** `backend/routers/chain.py` (new route), `backend/schemas.py` (no new schema needed — endpoint takes no body)

**What to build:**
- `GET /api/chain/diff` that reads `chain_control.json` and `chain_test.json`
- Node-level diff: for each step, compute `delta_influence` and `status` for every node in the union of both subgraphs
- Returns array of `diff_step` objects (defined in Data Flow above)
- Write result to `results/chain_diff.json` and serve from cache on subsequent calls

**Why first:** Everything else depends on this payload shape. Define the shape here before building the frontend.

**Dependency:** None beyond existing files on disk.

### Step 2: API Client Wrapper

**Files:** `frontend/src/api.js`

**What to build:**
- `getDiff()` function following the `getChainResults()` pattern
- Optionally add `getDiffCached()` that checks `chain_diff.json` endpoint first

**Why second:** DiffScreen needs this before it can fetch data.

**Dependency:** Step 1 (endpoint must exist to test the wrapper).

### Step 3: DiffBorgesGraph Component

**Files:** `frontend/src/components/DiffBorgesGraph.jsx`

**What to build:**
- Accepts `diffSteps` array, `viewMode` ("side-by-side" | "overlay"), `currentStep`
- Side-by-side: two BorgesGraph-like SVG panels sharing a step index
- Overlay: single SVG with control nodes (black) + test nodes (red), delta encoding in orange
- Node size: `abs(influence)`, delta status encoded in color per RawBlock palette
- Expose `onStepChange` callback for slider

**Why third:** Pure presentational component. Can be built and tested with mock diff data before DiffScreen wires it to live data.

**Dependency:** Diff payload shape from Step 1.

### Step 4: DiffScreen (Step 06)

**Files:** `frontend/src/screens/DiffScreen.jsx`, `frontend/src/App.jsx` (add step 06 to STEPS array)

**What to build:**
- Poll `getChainStatus()` → when ready, call `getDiff()`
- Step slider (0 to N-1)
- View mode toggle (side-by-side / overlay)
- Node filter toggles (added / suppressed / amplified / unchanged)
- Mount `DiffBorgesGraph` with live data

**Why last:** Orchestrates all prior components.

**Dependency:** Steps 1–3.

---

## Chain State Invalidation (Prerequisite)

The PROJECT.md lists "Chain state invalidation" as an active requirement. This must be addressed before or alongside the diff feature, because:

- If the user fires a new experiment, `chain_control.json`, `chain_test.json`, and `chain_diff.json` must all be cleared
- The current `_chain_state` dict is not reset on new experiment fire
- The diff endpoint would serve stale diff data from the previous experiment if invalidation is not handled

**Required change:** In `backend/routers/experiment.py`, when `POST /api/experiment/fire` is called, reset `_chain_state` to `{"state": "idle", ...}` and delete `chain_control.json`, `chain_test.json`, `chain_diff.json` before starting the background thread.

---

## Scalability Considerations

| Concern | At current scale | If chains grow |
|---------|-----------------|----------------|
| Diff computation time | Negligible (6 steps × 40 nodes = 240 nodes per chain) | Linear in steps × nodes; still cheap up to 100 steps |
| JSON payload size | Small (~50KB per chain JSON) | Manageable; diff JSON is smaller than either chain |
| Rate limits | Only chains already built; diff uses no external API | Rate limit pressure unchanged by diff feature |
| Concurrent users | Disk files are per-experiment, single-user tool | No change; not a multi-user tool |

---

## Existing Data Already Available

The `GET /api/chain/results` endpoint already exists and returns:

```json
{
  "control": { ...CompiledGraph.to_dict() },
  "test": { ...CompiledGraph.to_dict() }
}
```

The diff endpoint can reuse this exact data load pattern — read both files, diff in Python, return diff payload. No new library dependencies required. The diff logic is pure Python set/dict operations on the node and link arrays.

---

## Sources

- Direct codebase analysis: `borges_graph.py`, `backend/routers/chain.py`, `frontend/src/screens/FocalLineScreen.jsx`
- Data structure derived from `CompiledGraph.to_dict()` and `Step` dataclass (lines 85–101 of `borges_graph.py`)
- Node types and fields observed from `_build_focal_scene()` in `chain.py` (lines 125–227)
- Existing BorgesGraph SVG component analyzed from `FocalLineScreen.jsx` (lines 10–58)
