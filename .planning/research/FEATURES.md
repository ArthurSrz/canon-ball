# Feature Landscape

**Domain:** LLM interpretability experiment instrument (knowledge-injection measurement + attribution graph visualization)
**Researched:** 2026-06-08
**Confidence:** MEDIUM — table stakes from ecosystem survey (Neuronpedia, Anthropic attribution graphs, TransformerLens); differentiators from first-principles reasoning about Canon Ball's specific research question

---

## Table Stakes

Features researchers expect from any interpretability experiment tool. Missing = tool feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Paired experiment (control vs test) | Interpretability research is inherently contrastive — single-condition results are uninterpretable | Low | Already built in `canon_experiment.py` |
| UMAP / semantic embedding projection | Standard visualization for high-dimensional output distributions; researchers won't trust dispersion numbers without visual confirmation | Medium | Already built in `canon_analysis.py` + MapScreen |
| Statistical significance test | Results without p-values or effect size are not publishable; Mann-Whitney U is the right choice for non-parametric distributions | Low | Already built |
| Attribution graph for a single run | Circuit Tracer / feature attribution is the current standard for mechanistic interp; any tool not showing attribution is behind the SOTA | High | Already built via Neuronpedia + borges_graph.py |
| NLA verbalization of features | Researchers need natural-language labels on features — raw feature IDs are opaque | Medium | Already built via neuronpedia_client.py |
| Experiment configuration UI | Researchers must be able to set prompt, knowledge layer, and injection mode without editing code | Low | Already built in SetupScreen |
| Loading / async feedback | Chain computation takes 30-120s; users abandon without visible progress | Low | Partial — polling exists, needs cleaner status display |
| Results persistence within session | Navigating between screens must not lose results | Low | Already built (disk persistence + React state) |
| Error messaging | API failures (rate limit, timeout) must surface as readable messages, not blank screens | Low | Partial — error states exist but UI messaging is minimal |

---

## Differentiators

Features that are not expected by default but create research value Canon Ball can own.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Differential Borges graph** (control vs test side-by-side or overlaid) | Directly answers "which tokens did the knowledge layer activate?" — this is the core research question; no other tool does control/test attribution diff in one view | High | The new milestone. Data exists (two chains computed), needs visualization layer. Unique because Anthropic's open-sourced frontend shows single graphs only. |
| Injection mode as first-class experimental variable | Four modes (system_user, interleave, template, cot_priming) let researchers test HOW knowledge is injected, not just whether it was | Medium | Already built. Most tools treat prompt structure as fixed. |
| Focal Line scene (convergence visualization) | Maps attribution subgraph + NLA verbalizations into a left-right "path to prediction" view; more legible than a raw force-directed graph for non-experts | Medium | Already built. Unusual in the ecosystem — most tools show raw graphs. |
| Dispersion tightening as primary metric | Framing semantic coherence as "landing zone tightening %" is more intuitive than raw cosine distance; lets researchers compare across experiments | Low | Already built, needs surfacing in UI copy. |
| Chain-centric design (WHY and WHAT in same instrument) | Most tools answer either the statistical question or the mechanistic question; Canon Ball answers both from one experiment fire | High | Architectural commitment already made. Payoff requires differential Borges graph to complete the WHY. |
| RawBlock brutalist design with semantic color encoding | control=black, test=red, knowledge=orange is a consistent visual language that makes comparison effortless across screens | Low | Already built in styles.css. |

---

## Anti-Features

Features to deliberately NOT build. Building these would bloat scope, dilute the instrument, or conflict with the research model.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Persistent experiment history / cross-run comparison | Adds auth, storage, and a data model — none of which are needed for a publish-once research instrument | Session-scoped results only; researchers export screenshots/data manually |
| Multi-model comparison | Doubles every API call, complicates the attribution layer (Circuit Tracer is gemma-2-2b locked), and the research question is model-agnostic | Single model per session; model choice can be a config option later |
| Fine-grained feature steering UI | SAE feature IDs are preserved for future steering, but building a full steering interface (like Neuronpedia's) is a different product | Preserve `feature` field in CompiledGraph; steering is v2+ |
| Authentication / user accounts | No persistence = no auth needed; adds infra complexity for zero researcher benefit in v1 | API key in .env; public deployment without login |
| Free-form graph editing (add/remove nodes) | Researchers are reading attribution, not constructing it; editing introduces error | Read-only graph with expand/collapse for visual clarity only |
| RAG / retrieval as injection mode | Changes the research question from "what does a knowledge layer do" to "what does retrieval do" — different instrument | System prompt layer only, explicitly documented |
| Animated graph transitions | Pretty but distracting in a research context; risks obscuring actual data changes | Static render with clear before/after states |

---

## Feature Dependencies

```
Experiment engine (fire N trials)
  → Embedding + UMAP projection (MapScreen)
    → Dispersion metrics + Mann-Whitney U (MetricsScreen)
  → Background chain computation (control + test CompiledGraph)
    → Focal Line scene (FocalLineScreen) [single chain, existing]
    → Differential Borges graph [NEW — requires both chains, needs new screen/component]

Injection modes
  → Experiment engine (mode is a FireRequest parameter)
  → ModesScreen (comparison across modes — requires multiple experiment fires)

NLA verbalization
  → Focal Line scene (diverge nodes are NLA descriptions)
  → Differential Borges graph (node labels in diff view)

Chain state invalidation [Active requirement]
  → All chain-dependent screens (FocalLine, Differential Borges)
  → Must reset on new experiment fire to prevent stale chain display
```

---

## MVP Recommendation

The current codebase is already past MVP for the statistical/semantic instrument. The gap is the **differential Borges graph**, which is the feature that completes Canon Ball's WHY instrument and makes the chain-centric design pay off.

**Prioritize for next milestone:**
1. Differential Borges graph — side-by-side SVG with shared node vocabulary, edges colored by presence in control (black) / test (red) / both (gray)
2. Chain state invalidation — prevents "stuck computing" state that breaks the diff view
3. Backend detection fix — eliminates 1.5s blocking that degrades perceived experiment start speed

**Defer:**
- Streamlit removal — useful cleanup but zero researcher-facing impact; do after differential graph ships
- Published tool readiness (CORS lock, rate limiting) — necessary before sharing publicly, but not before the core feature works

---

## Sources

- [Anthropic open-sourcing circuit-tracing tools](https://www.anthropic.com/research/open-source-circuit-tracing) — HIGH confidence, official release
- [Anthropic attribution-graphs-frontend (GitHub)](https://github.com/anthropics/attribution-graphs-frontend) — HIGH confidence, source code
- [Circuit Tracing: Revealing Computational Graphs in Language Models](https://transformer-circuits.pub/2025/attribution-graphs/methods.html) — HIGH confidence, methodology paper
- [Neuronpedia open source platform (GitHub)](https://github.com/hijohnnylin/neuronpedia) — HIGH confidence
- [Circuits Research Landscape, Neuronpedia 2025](https://www.neuronpedia.org/graph/info) — MEDIUM confidence (site, not paper)
- [Summit: Scaling Deep Learning Interpretability](https://fredhohman.com/summit/) — MEDIUM confidence, comparative visualization research
- Differential graph comparison noted as an open research opportunity in Summit (2019) but not yet standard in LLM interpretability tools as of 2026 — LOW confidence (training data + ecosystem inference)
