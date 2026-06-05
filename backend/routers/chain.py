"""Chain endpoints — attribution tracing and focal line scene building."""

import json
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.schemas import TraceRequest, FocalRequest
import borges_graph as bg
import neuronpedia_client as npc

router = APIRouter()
RESULTS_DIR = Path("results")

_chain_state: dict = {"state": "idle", "step": 0, "total": 0, "error": None}
_chain_lock = threading.Lock()


def _update_chain_state(**kwargs):
    with _chain_lock:
        _chain_state.update(kwargs)


# Initialize from disk state on module load (handles server restarts)
if (RESULTS_DIR / "chain_control.json").exists() and (RESULTS_DIR / "chain_test.json").exists():
    _chain_state.update({"state": "ready", "step": 2, "total": 2})


def start_chains_bg(prompt: str, knowledge_layer: str, max_tokens: int = 6):
    """Called by experiment router after UMAP completes. Runs in background thread."""
    def _run():
        _update_chain_state(state="computing", step=0, total=2 * max_tokens, error=None)
        try:
            RESULTS_DIR.mkdir(exist_ok=True)

            def make_on_step(chain_idx):
                def on_step(step_obj):
                    _update_chain_state(step=chain_idx * max_tokens + step_obj.index + 1)
                return on_step

            ctrl = bg.compile_attribution(prompt, system_prompt="", max_tokens=max_tokens,
                                          on_step=make_on_step(0))
            (RESULTS_DIR / "chain_control.json").write_text(
                json.dumps(ctrl.to_dict(), indent=2)
            )
            _update_chain_state(step=max_tokens)

            test = bg.compile_attribution(prompt, system_prompt=knowledge_layer,
                                          max_tokens=max_tokens, on_step=make_on_step(1))
            (RESULTS_DIR / "chain_test.json").write_text(
                json.dumps(test.to_dict(), indent=2)
            )
            _update_chain_state(state="ready", step=2 * max_tokens)
            print("Borges chains saved.", flush=True)
        except Exception as e:
            _update_chain_state(state="failed", error=str(e))
            print(f"Chain pre-compute failed: {e}", flush=True)

    threading.Thread(target=_run, daemon=True).start()


@router.get("/status")
def get_chain_status():
    with _chain_lock:
        return dict(_chain_state)


@router.get("/results")
def get_chain_results():
    """Return pre-computed Borges chains (written by experiment fire)."""
    ctrl_path = RESULTS_DIR / "chain_control.json"
    test_path = RESULTS_DIR / "chain_test.json"

    if not ctrl_path.exists():
        raise HTTPException(404, "Chains not yet computed. Fire an experiment first.")

    ctrl = json.loads(ctrl_path.read_text())
    test = json.loads(test_path.read_text()) if test_path.exists() else None
    return {"control": ctrl, "test": test}


@router.post("/trace")
def trace_chain(req: TraceRequest):
    graph = bg.compile_attribution(
        prompt=req.prompt,
        system_prompt=req.system_prompt,
        max_tokens=req.max_tokens,
    )
    return graph.to_dict()


@router.post("/focal")
def build_focal(req: FocalRequest):
    """Build the focal line scene: Circuit Tracer (converge) + NLA (diverge).

    Returns the shape expected by the FocalLine React component:
    {inputs, converge, focus, answer, diverge}
    """
    context = (req.knowledge_layer + "\n\n" + req.prompt).strip() if req.knowledge_layer else req.prompt

    attrib = npc.generate_attribution_graph(req.prompt)
    subgraph = None
    if attrib.get("ok") and attrib.get("s3url"):
        subgraph = npc.fetch_attribution_subgraph(attrib["s3url"], max_nodes=40, max_links=200)

    nla_result = npc.verbalize_activations(
        prompt=req.prompt,
        model=req.nla_model,
        source=req.nla_source,
        system=req.knowledge_layer or None,
        max_tokens=req.nla_max_tokens,
    )

    scene = _build_focal_scene(req.prompt, req.knowledge_layer, subgraph, nla_result)
    scene["meta"] = {
        "attribution_url": attrib.get("url"),
        "attribution_ok": attrib.get("ok", False),
        "nla_model": req.nla_model,
        "nla_truncated": nla_result.truncated if nla_result else False,
    }
    return scene


def _build_focal_scene(prompt: str, knowledge_layer: str, subgraph: dict | None, nla_result) -> dict:
    """Map Circuit Tracer subgraph + NLA result into the focal line visualization shape."""

    # --- Inputs (left side): prompt tokens + optional knowledge node ---
    prompt_words = prompt.split()
    inputs = [{"id": w.lower().strip("?.!,"), "label": w, "kind": "prompt"} for w in prompt_words]
    if knowledge_layer:
        inputs.append({"id": "know", "label": "knowledge layer", "kind": "know"})

    # --- Converge (middle): feature nodes from subgraph ---
    converge = []
    focus = {"label": "?", "p": 0.0}
    answer = ""

    if subgraph and subgraph.get("ok"):
        nodes = subgraph.get("nodes", [])
        links = subgraph.get("links", [])

        node_map = {n["id"]: n for n in nodes}
        embedding_ids = {n["id"] for n in nodes if n.get("type") == "embedding"}
        logit_nodes = [n for n in nodes if n.get("type") == "logit"]
        feature_nodes = [n for n in nodes if n.get("type") == "cross layer transcoder"]

        feature_nodes.sort(key=lambda n: abs(n.get("influence", 0)), reverse=True)
        top_features = feature_nodes[:6]

        for fn in top_features:
            from_ids = []
            for link in links:
                if link["target"] == fn["id"] and link["source"] in embedding_ids:
                    src = node_map.get(link["source"], {})
                    label = src.get("label", "").strip()
                    word = label.lower().strip("?.!,")
                    if word and any(inp["id"] == word for inp in inputs):
                        from_ids.append(word)
                    elif knowledge_layer and link["source"] in embedding_ids:
                        pass

            for link in links:
                if link["target"] == fn["id"]:
                    src = node_map.get(link["source"], {})
                    if src.get("type") == "cross layer transcoder" and "knowledge" in src.get("label", "").lower():
                        from_ids.append("know")

            if not from_ids:
                from_ids = [inputs[0]["id"]] if inputs else []

            is_from_knowledge = "know" in from_ids
            converge.append({
                "id": fn["id"],
                "label": fn.get("label", f"feature L{fn.get('layer', '?')}"),
                "from": from_ids,
                "w": min(1.0, abs(fn.get("influence", 0.5))),
                "note": fn.get("label", ""),
                "gold": is_from_knowledge,
                "hot": fn.get("influence", 0) > 0.8,
            })

        if logit_nodes:
            target = next((n for n in logit_nodes if n.get("is_target")), logit_nodes[0])
            label_text = target.get("label", "")
            import re
            m = re.search(r'"([^"]+)"', label_text)
            token = m.group(1).strip() if m else label_text.split()[0] if label_text else "?"
            focus = {"label": token.strip("▁ "), "p": round(target.get("prob", 0), 2)}

    # --- Answer: from NLA response ---
    if nla_result and nla_result.response:
        answer = nla_result.response
    elif focus["label"] != "?":
        answer = focus["label"]

    # --- Diverge (right side): NLA verbalizations of answer tokens ---
    diverge = []
    if nla_result and nla_result.features:
        prompt_len = nla_result.prompt_length or 0
        answer_features = [f for f in nla_result.features if f.position >= prompt_len]
        seen = set()
        for feat in answer_features:
            token = feat.token.strip()
            if not token or token in seen or len(token) < 2:
                continue
            seen.add(token)
            diverge.append({
                "id": f"d-{feat.position}",
                "token": token,
                "why": feat.description,
            })
            if len(diverge) >= 5:
                break

    if not converge:
        converge = [{"id": "placeholder", "label": "(attribution unavailable)", "from": [inputs[0]["id"]] if inputs else [], "w": 0.5, "note": "Circuit Tracer did not return features", "gold": False, "hot": False}]
    if not diverge:
        diverge = [{"id": "d-0", "token": focus["label"], "why": "(NLA verbalizations unavailable)"}]

    return {
        "inputs": inputs,
        "converge": converge,
        "focus": focus,
        "answer": answer,
        "diverge": diverge,
    }
