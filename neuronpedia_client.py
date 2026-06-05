"""
Neuronpedia NLA (Natural Language Autoencoder) client — the canon ball's "internal mirror".

Where canon_experiment.py measures the *output* side of an LLM (embedding dispersion of its
answers), this module opens the *internal* mirror: it asks Neuronpedia's Activation Verbalizer to
describe, in natural language, what the model encodes at each token of a prompt. Those per-token
descriptions are the model's "graphe de fonctions" — the internal counterpart to the external
knowledge graph ("graphe de sens") the canon ball already manipulates.

Vertical slice scope: read-only verbalization + a basic attribution-style feature graph.
No steering / interventions yet (that is the next phase).

API contract is documented in troubleshooting.md. The three relevant routes:
  GET  /api/nla/sources      — list (modelId, nlaSourceId, layerNum) pairs
  POST /api/nla/completion    — generate a response + NLA token list (best-effort; may 500)
  POST /api/nla/explain       — natural-language description of activations at token positions

Auth is optional; a key (header `x-api-key`) only raises rate limits. Explain caps at 16 *new*
token positions per request.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import requests

NP_BASE = "https://www.neuronpedia.org"
DEFAULT_MODEL = "gemma-3-27b-it"
DEFAULT_SOURCE = "kitft-l41"  # Layer 41 NLA for gemma-3-27b-it
MAX_NEW_POSITIONS = 16  # hard server limit (MAX_TOKENS_TO_EXPLAIN)
_TIMEOUT = 90


# ── Auth (mirrors canon_experiment._get_openrouter_key) ───────────────────────


def _np_key() -> str:
    """Resolve the Neuronpedia API key from backend config, then env. May be empty (auth is optional)."""
    try:
        from backend.config import neuronpedia_key
        return neuronpedia_key()
    except ImportError:
        pass
    return os.environ.get("NEURONPEDIA_API_KEY", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    key = _np_key()
    if key:
        h["x-api-key"] = key
    return h


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Feature:
    """One verbalized activation: what the model encodes at a single token position."""

    position: int
    token: str
    description: str
    l2_norm: float = 0.0
    cosine_similarity: float = 0.0
    mse: float = 0.0

    def short_label(self) -> str:
        """First sentence of the verbalization — a compact node label for the graph."""
        text = (self.description or "").strip().replace("\n", " ")
        for sep in (". ", "; ", ": "):
            if sep in text:
                return text.split(sep)[0].strip()
        return text[:80]


@dataclass
class NLAResult:
    prompt: str
    model: str
    source: str
    layer_index: int = 0
    prompt_length: int = 0
    features: list[Feature] = field(default_factory=list)
    response: str | None = None  # filled only if /completion succeeded
    truncated: bool = False  # True if prompt had more tokens than max_tokens allowed
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.features)


# ── Raw API calls ───────────────────────────────────────────────────────────


def list_sources() -> list[dict]:
    """GET /api/nla/sources. Raises on transport error."""
    resp = requests.get(f"{NP_BASE}/api/nla/sources", headers=_headers(), timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("sources", [])


def _explain(
    *,
    positions: list[int],
    model: str,
    source: str,
    text: str | None = None,
    messages: list[dict] | None = None,
    temperature: float = 0.7,
) -> dict:
    """POST /api/nla/explain. Supply `text` (chat-templated) OR `messages`."""
    body: dict = {
        "modelId": model,
        "nlaSourceId": source,
        "positions": positions,
        "temperature": temperature,
    }
    if text is not None:
        body["text"] = text
    else:
        body["messages"] = messages
    resp = requests.post(f"{NP_BASE}/api/nla/explain", json=body, headers=_headers(), timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"explain {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _completion(prompt: str, model: str, temperature: float, completion_tokens: int) -> dict | None:
    """POST /api/nla/completion — best-effort. Returns None on any failure (endpoint can 500)."""
    try:
        resp = requests.post(
            f"{NP_BASE}/api/nla/completion",
            json={
                "modelId": model,
                "messages": [{"role": "user", "content": prompt}],
                "completion_tokens": min(completion_tokens, 512),
                "temperature": temperature,
            },
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


# ── High-level entry point ────────────────────────────────────────────────────


def _feature_from_record(r: dict) -> Feature | None:
    if not r.get("description"):
        return None
    return Feature(
        position=int(r.get("position", -1)),
        token=str(r.get("token", "")),
        description=str(r.get("description", "")),
        l2_norm=float(r.get("l2_norm", 0.0) or 0.0),
        cosine_similarity=float(r.get("cosine_similarity", 0.0) or 0.0),
        mse=float(r.get("mse", 0.0) or 0.0),
    )


def verbalize_activations(
    prompt: str,
    model: str = DEFAULT_MODEL,
    source: str = DEFAULT_SOURCE,
    system: str | None = None,
    max_tokens: int = 192,
    temperature: float = 0.7,
    progress=None,
) -> NLAResult:
    """
    Open the internal mirror: verbalize the model's activations at EVERY token position of the
    chat-templated prompt — including the knowledge layer (`system`) when provided.

    Note: the NLA API only accepts `user`/`assistant` roles, so `system` is folded into the user
    turn as a context preamble (the "template" injection style) rather than a real system message.

    The API caps each request at 16 *new* positions, but caches results by position, so we batch
    `[0..15], [16..31], …` until all positions (up to `max_tokens`) are covered. `progress`, if
    given, is called as `progress(done, total)` after each batch so the UI can show a bar.

    Robust to the flaky /completion endpoint (best-effort response enrichment) and to partial
    failures (keeps whatever batches succeeded).
    """
    user_content = prompt
    if system and system.strip():
        user_content = f"{system.strip()}\n\n{prompt}"
    messages: list[dict] = [{"role": "user", "content": user_content}]

    result = NLAResult(prompt=prompt, model=model, source=source)

    # 1. Best-effort response generation (enrichment only).
    comp = _completion(user_content, model, temperature, completion_tokens=64)
    if comp and isinstance(comp.get("completion"), str):
        result.response = comp["completion"]

    # 2. Probe for prompt_length (a cheap 1-position explain).
    try:
        probe = _explain(positions=[0], model=model, source=source, messages=messages, temperature=temperature)
    except Exception as e:
        result.error = f"Neuronpedia NLA unavailable: {e}"
        return result

    result.layer_index = int(probe.get("layer_index", 0))
    result.prompt_length = int(probe.get("prompt_length", 0))
    if result.prompt_length <= 0:
        result.error = "NLA returned an empty prompt tokenization."
        return result

    # 3. Explain EVERY position, batching through the 16-new-positions-per-request cap.
    total = min(result.prompt_length, max(max_tokens, 1))
    result.truncated = total < result.prompt_length
    records: dict[int, dict] = {}
    for start in range(0, total, MAX_NEW_POSITIONS):
        batch = list(range(start, min(start + MAX_NEW_POSITIONS, total)))
        try:
            data = _explain(positions=batch, model=model, source=source,
                            messages=messages, temperature=temperature)
        except Exception as e:
            if not records:  # nothing succeeded at all → hard error
                result.error = f"NLA explain failed: {e}"
                return result
            break  # partial success: keep the batches we already have
        result.layer_index = int(data.get("layer_index", result.layer_index))
        for r in data.get("results", []):
            p = r.get("position")
            if isinstance(p, int):
                records[p] = r
        if progress:
            progress(min(start + MAX_NEW_POSITIONS, total), total)

    result.features = [f for p in sorted(records) if (f := _feature_from_record(records[p]))]
    if not result.features:
        result.error = "NLA returned no descriptions for the requested positions."
    return result


# ── Real attribution graph (Circuit Tracer) ──────────────────────────────────

GRAPH_MODEL = "gemma-2-2b"  # only model with on-demand attribution graphs
_GRAPH_TIMEOUT = 200


def generate_attribution_graph(prompt: str, model: str = GRAPH_MODEL, slug_prefix: str = "canonball") -> dict:
    """
    Generate a real causal attribution graph (Circuit Tracer / the biology paper) via
    POST /api/graph/generate. Unlike the NLA (which *describes* each token), this returns the
    causal circuit — feature nodes and attribution-weighted links flowing to the answer's logits.

    Constraints: gemma-2-2b only, prompt capped at 64 tokens, GPU-backed (slow, can be busy).
    Returns a dict: {ok, url, s3url, num_nodes, num_links, error}. The `url` is Neuronpedia's
    interactive viewer (embeddable in an iframe).
    """
    import re
    import time as _t

    base = re.sub(r"[^a-z0-9_-]", "", prompt.lower().replace(" ", "-"))[:16] or "graph"
    slug = f"{slug_prefix}-{base}-{int(_t.time())}"
    try:
        resp = requests.post(
            f"{NP_BASE}/api/graph/generate",
            json={"prompt": prompt, "modelId": model, "slug": slug},
            headers=_headers(),
            timeout=_GRAPH_TIMEOUT,
        )
    except Exception as e:
        return {"ok": False, "error": f"Attribution graph request failed: {e}"}

    if resp.status_code == 200:
        d = resp.json()
        return {
            "ok": True,
            "url": d.get("url", ""),
            "s3url": d.get("s3url", ""),
            "num_nodes": d.get("numNodes", 0),
            "num_links": d.get("numLinks", 0),
        }
    # Surface the API's own message (prompt too long / GPUs busy / etc.).
    try:
        msg = resp.json().get("message") or resp.json().get("error")
    except Exception:
        msg = resp.text[:200]
    busy = resp.status_code == 503
    return {"ok": False, "error": f"{msg or ('GPUs busy' if busy else resp.status_code)}", "busy": busy}


# ── Attribution graph (NLA descriptive view) ─────────────────────────────────


def build_attribution_graph(nla: NLAResult) -> dict:
    """
    Build a basic attribution-style graph: prompt → {feature per token position} → response.

    Honors the project's graph ontology (CLAUDE.md):
      - no orphan nodes: every feature links to both the prompt and response core nodes;
      - every edge carries a `weight` attribute;
      - every feature node has properties (token, description, position, activation norm);
      - the prompt/response "core" nodes anchor the graph.

    Returns {"nodes": [...], "edges": [...]} as plain JSON for the SVG renderer.
    """
    # Normalize activation magnitude into a 0..1 edge weight so the renderer can scale strokes.
    norms = [f.l2_norm for f in nla.features if f.l2_norm > 0]
    max_norm = max(norms) if norms else 1.0

    nodes: list[dict] = [
        {"id": "prompt", "group": "core", "label": "PROMPT", "title": nla.prompt},
        {
            "id": "response",
            "group": "core",
            "label": "RESPONSE",
            "title": nla.response or "(response generation unavailable)",
        },
    ]
    edges: list[dict] = []

    for f in nla.features:
        norm_w = (f.l2_norm / max_norm) if max_norm else 0.5
        weight = round(0.15 + 0.85 * norm_w, 4)  # keep edges visible even for small norms
        node_id = f"f{f.position}"
        nodes.append(
            {
                "id": node_id,
                "group": "feature",
                "label": f.token.strip() or f"#{f.position}",
                "summary": f.short_label(),
                "description": f.description,
                "position": f.position,
                "l2_norm": f.l2_norm,
                "cosine_similarity": f.cosine_similarity,
                "weight": weight,
            }
        )
        # prompt → feature → response (no orphans; both edges carry a weight)
        edges.append({"source": "prompt", "target": node_id, "weight": weight})
        edges.append({"source": node_id, "target": "response", "weight": weight})

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "model": nla.model,
            "source": nla.source,
            "layer_index": nla.layer_index,
            "prompt_length": nla.prompt_length,
            "feature_count": len(nla.features),
            "truncated": nla.truncated,
        },
    }


# ── Mise en abîme scene: prune attribution + map both models onto words ───────


def fetch_attribution_subgraph(s3url: str, max_nodes: int = 50, max_links: int = 240) -> dict:
    """
    Fetch a generated CLTGraph JSON and prune it to a renderable subgraph: the top `max_nodes`
    feature nodes by `influence`, plus all input `embedding` nodes and the top output `logit`
    nodes (the answer). Keeps only links between retained nodes (top `max_links` by |weight|).

    Returns {ok, nodes, links, prompt_tokens, max_layer, error}. Each node is compact:
    {id, layer, ctx_idx, type, influence, label, prob, is_target}.
    """
    try:
        resp = requests.get(s3url, timeout=90)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"ok": False, "error": f"Could not fetch attribution graph: {e}"}

    raw_nodes = data.get("nodes", [])
    raw_links = data.get("links", [])
    prompt_tokens = data.get("metadata", {}).get("prompt_tokens", [])

    embeddings = [n for n in raw_nodes if n.get("feature_type") == "embedding"]
    logits = [n for n in raw_nodes if n.get("feature_type") == "logit"]
    feats = [n for n in raw_nodes if n.get("feature_type") == "cross layer transcoder"]

    feats.sort(key=lambda n: n.get("influence") or 0.0, reverse=True)
    kept_feats = feats[:max_nodes]
    logits.sort(key=lambda n: n.get("token_prob") or 0.0, reverse=True)
    kept_logits = [n for n in logits if n.get("is_target_logit")][:1] + logits[:5]

    kept, kept_ids = [], set()
    for n in embeddings + kept_feats + kept_logits:  # dedupe (target logit may repeat)
        if n["node_id"] not in kept_ids:
            kept_ids.add(n["node_id"])
            kept.append(n)

    numeric_layers = [int(n["layer"]) for n in kept if str(n.get("layer", "")).isdigit()]
    max_layer = max(numeric_layers) if numeric_layers else 1

    def _depth(n: dict) -> int:
        if n.get("feature_type") == "embedding":
            return 0
        if n.get("feature_type") == "logit":
            return max_layer + 2
        return int(n["layer"]) + 1 if str(n.get("layer", "")).isdigit() else 1

    nodes = [
        {
            "id": n["node_id"],
            "feature": n.get("feature"),
            "layer": n.get("layer"),
            "depth": _depth(n),
            "ctx_idx": n.get("ctx_idx", 0),
            "type": n.get("feature_type"),
            "influence": float(n.get("influence") or 0.0),
            "label": n.get("clerp") or "",
            "prob": float(n.get("token_prob") or 0.0),
            "is_target": bool(n.get("is_target_logit")),
        }
        for n in kept
    ]

    links = [
        {"source": l["source"], "target": l["target"], "weight": float(l.get("weight", 0.0))}
        for l in raw_links
        if l.get("source") in kept_ids and l.get("target") in kept_ids
    ]
    links.sort(key=lambda l: abs(l["weight"]), reverse=True)
    links = links[:max_links]

    return {
        "ok": True,
        "nodes": nodes,
        "links": links,
        "prompt_tokens": prompt_tokens,
        "max_depth": max_layer + 2,
    }


def _words_with_spans(text: str) -> list[dict]:
    """Split text into words, each with its character span and a stable index."""
    import re

    return [
        {"i": i, "text": m.group(0), "start": m.start(), "end": m.end()}
        for i, m in enumerate(re.finditer(r"\S+", text))
    ]


def _map_tokens_to_words(token_texts: list[str], words: list[dict], base_offset: int, shift: int) -> list[int | None]:
    """
    Map an ordered token stream to word indices by reconstructing char offsets.

    Tokenizers are reversible by concatenation (token strings carry their leading spaces), so we
    rebuild each token's span in the concatenated stream, translate it into `words` coordinates via
    `base_offset` (where the meaningful text begins in the stream) and `shift` (where that text sits
    in the words' reference text), then bin by midpoint. Returns a word index per token (or None).
    """
    out: list[int | None] = []
    cur = 0
    for t in token_texts:
        mid = cur + len(t) / 2.0
        cur += len(t)
        pos = (mid - base_offset) + shift
        wi = next((w["i"] for w in words if w["start"] <= pos < w["end"]), None)
        if wi is None and words:  # nearest-word fallback keeps every token attached
            wi = min(words, key=lambda w: abs((w["start"] + w["end"]) / 2 - pos))["i"]
        out.append(wi)
    return out


def build_mise_en_abime_scene(prompt: str, knowledge: str | None, nla: NLAResult, attrib: dict | None) -> dict:
    """
    Assemble the unified scene: a central spine of words, left NLA "roots" (one verbalization per
    word), and a right attribution "tree" (pruned feature nodes mapped onto prompt words, growing
    by layer to the answer logits). Tokenizations of the two models are reconciled onto human words.
    """
    sys = (knowledge or "").strip()
    user_content = f"{sys}\n\n{prompt}" if sys else prompt
    words = _words_with_spans(user_content)
    prompt_start = user_content.rfind(prompt) if prompt else 0
    for w in words:
        w["role"] = "prompt" if w["start"] >= prompt_start else "context"

    # ── Left roots: NLA features → words ──
    roots_by_word: dict[int, dict] = {}
    if nla is not None and nla.ok:
        feats = sorted(nla.features, key=lambda f: f.position)
        templated = "".join(f.token for f in feats)
        base = templated.find(user_content)
        if base < 0:  # fallback: assume content is the tail of the templated stream
            base = max(0, len(templated) - len(user_content))
        token_words = _map_tokens_to_words([f.token for f in feats], words, base_offset=base, shift=0)
        for f, wi in zip(feats, token_words):
            if wi is None:
                continue
            cur = roots_by_word.get(wi)
            if cur is None or f.l2_norm > cur["l2"]:
                roots_by_word[wi] = {"word_index": wi, "label": f.short_label(),
                                     "full": f.description, "l2": f.l2_norm}
    roots = list(roots_by_word.values())

    # ── Right tree: attribution ctx_idx → prompt word ──
    tree: dict = {"nodes": [], "links": [], "max_depth": 0}
    if attrib and attrib.get("ok"):
        ptoks = attrib.get("prompt_tokens", [])
        recon = "".join(ptoks)
        pbase = recon.find(prompt)
        if pbase < 0:
            pbase = max(0, len(recon) - len(prompt))
        # ctx_idx (token position) → word index in the full words list
        ctx_words = _map_tokens_to_words(ptoks, words, base_offset=pbase, shift=prompt_start)
        ctx_to_word = {i: wi for i, wi in enumerate(ctx_words)}
        prompt_word_idxs = [w["i"] for w in words if w["role"] == "prompt"]
        fallback_word = prompt_word_idxs[len(prompt_word_idxs) // 2] if prompt_word_idxs else 0

        for n in attrib["nodes"]:
            wi = ctx_to_word.get(n.get("ctx_idx", 0))
            n2 = dict(n)
            n2["word_index"] = wi if wi is not None else fallback_word
            tree["nodes"].append(n2)
        tree["links"] = attrib["links"]
        tree["max_depth"] = attrib.get("max_depth", 0)

    return {
        "words": words,
        "roots": roots,
        "tree": tree,
        "meta": {
            "nla_model": nla.model if nla is not None else "",
            "attrib_model": GRAPH_MODEL,
            "nla_ok": bool(nla and nla.ok),
            "attrib_ok": bool(attrib and attrib.get("ok")),
            "word_count": len(words),
            "prompt_word_count": sum(1 for w in words if w["role"] == "prompt"),
        },
    }


def build_lens_scene(prompt: str, knowledge: str | None, nla: NLAResult | None,
                     attrib: dict | None, answer: str | None = None, n_rays: int = 5) -> dict:
    """Reduce the mirror to the focal-lines optical-bench scene (LensView.jsx).

    Picks the n brightest NLA features (by l2_norm) as rays; each ray carries an
    attribution label (the feature's compact description) and a NLA "why" (the
    full first-sentence verbalization that explains why this feature fires).
    """
    feats = sorted((nla.features if (nla and nla.ok) else []),
                   key=lambda f: f.l2_norm, reverse=True)[:n_rays]
    attrib_labels: list[str] = []
    if attrib and attrib.get("ok"):
        attrib_labels = [n.get("label", "") for n in
                         sorted([n for n in attrib.get("nodes", []) if n.get("type") == "feature"],
                                key=lambda n: n.get("influence", 0), reverse=True)]
    rays: list[dict] = []
    # 5 vertically-distributed ray slots that match the LensView geometry (700-unit canvas).
    SLOT_SY = [110, 235, 360, 470, 585]
    SLOT_LY = [175, 252, 350, 448, 525]
    SLOT_DY = [90, 230, 360, 490, 615]
    for i in range(min(n_rays, len(SLOT_SY))):
        f = feats[i] if i < len(feats) else None
        attr = (attrib_labels[i] if i < len(attrib_labels) and attrib_labels[i]
                else (f.short_label() if f else f"feature #{i+1}"))
        why = (f.short_label() if f
               else ("the lens recruited a feature the bare prompt did not"))
        rays.append({"sy": SLOT_SY[i], "ly": SLOT_LY[i], "dy": SLOT_DY[i],
                     "attr": (attr or "").strip()[:64],
                     "why": (why or "").strip()[:90]})
    return {
        "rays": rays,
        "source_label": "the throw · scattered prompt",
        "lens_label": "knowledge layer · the lens",
        "answer": (answer or "").strip() or "Resolved by the knowledge layer.",
        "meta": {
            "nla_model": nla.model if nla is not None else "",
            "attrib_model": GRAPH_MODEL,
            "nla_ok": bool(nla and nla.ok),
            "attrib_ok": bool(attrib and attrib.get("ok")),
            "n_rays": len(rays),
        },
    }
