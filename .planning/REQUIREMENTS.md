# Requirements: Canon Ball

**Defined:** 2026-06-08
**Core Value:** A researcher can fire one experiment and get a direct, visual answer to "what did this knowledge layer do to this model's output distribution?"

## v1 Requirements

### Data Integrity

- [ ] **INTG-01**: System resets chain state (control + test) when a new experiment fires, preventing stale chains from being served as current
- [ ] **INTG-02**: diff_graphs() joins control/test CompiledGraph nodes by SAE feature key (feature, depth, ctx_idx) not list index position
- [ ] **INTG-03**: Neuronpedia label parsing raises a structured error on format mismatch instead of silently substituting "?"

### Differential Graph

- [ ] **DIFF-01**: diff_graphs() pure Python function accepts two CompiledGraph objects and returns a delta-encoded diff with per-node status (added, removed, amplified, suppressed, unchanged) and delta_influence values
- [ ] **DIFF-02**: GET /api/chain/diff endpoint computes and returns the diff payload once both chains are ready
- [ ] **DIFF-03**: DiffBorgesGraph React component renders delta-encoded nodes as inline SVG using the RawBlock palette (orange=knowledge-added, red=suppressed, grey=shared/unchanged)
- [ ] **DIFF-04**: DiffScreen registers as step 6 in the existing 6-step rail navigation, wrapping DiffBorgesGraph

### Cleanup

- [ ] **CLEN-01**: Legacy Streamlit files (app.py, pages/, shared_sidebar.py, html_components.py) audited for unique test surface, then deleted
- [ ] **CLEN-02**: CANON_BACKEND asserted at application startup; lazy 1.5s Ollama probe eliminated
- [ ] **CLEN-03**: allow_origins restricted to explicit domain list via ALLOWED_ORIGINS environment variable

## v2 Requirements

### Pipeline Stabilization

- **PIPE-01**: Concurrent /fire requests rejected or queued while an experiment is running
- **PIPE-02**: NLA token position alignment validated between control and test prompts before diff is rendered
- **PIPE-03**: Rate-limit (429) and GPU-unavailable (503) Neuronpedia states surfaced distinctly in the UI

### Rate Limiting

- **RLIM-01**: slowapi rate limiting applied to /api/experiment/fire to protect OpenRouter quota

## Out of Scope

| Feature | Reason |
|---------|--------|
| Persistent experiment history | Wrong product — configure+fire+read is the research pattern |
| Cross-run comparison | Requires persistence; out of v1 scope |
| Multi-model support | Attribution is gemma-2-2b locked via Neuronpedia; doubles complexity |
| Feature steering UI | SAE feature IDs preserved in CompiledGraph for future use; UI not now |
| RAG injection | Knowledge form is system prompt layer only |
| Fine-tuning / weight modification | Injection-time knowledge only |
| Animated graph transitions | Adds complexity with no research value |
| Free-form graph editing | Not a graph editor; a research instrument |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTG-01 | Phase 1 | Pending |
| INTG-02 | Phase 1 | Pending |
| INTG-03 | Phase 1 | Pending |
| DIFF-01 | Phase 2 | Pending |
| DIFF-02 | Phase 2 | Pending |
| DIFF-03 | Phase 2 | Pending |
| DIFF-04 | Phase 2 | Pending |
| CLEN-01 | Phase 3 | Pending |
| CLEN-02 | Phase 3 | Pending |
| CLEN-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-08 after initial definition*
