"""
Borges Graph — Compiled Attribution Graph Builder

Standalone library wrapping the Neuronpedia Circuit Tracer API. No Streamlit dependency.

Usage:
    from borges_graph import compile_attribution

    graph = compile_attribution(
        prompt="What is the capital of France?",
        max_tokens=5,
        on_step=lambda s: print(f"Step {s.index}: '{s.token}'"),
    )
    print(graph.generated_text)
    print(graph.to_dict())

Each step generates an attribution graph for the current context, extracts the
predicted token (top logit), records both, then appends only the generated token
to the context. The attribution graphs are observed — they're the causal record
of *why* each token was chosen.

Model constraints:
    - Circuit Tracer: gemma-2-2b only, 64-token prompt cap, rate limit 30/hr
      (a token-accurate gliding window keeps the context within that cap — see _sliding_window)
    - NLA verbalization runs on different models (gemma-3-27b, llama-3.3-70b) — not used here
    - Feature identifiers (SAE dictionary indices) are preserved for future steering
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable

import neuronpedia_client as npc


# Circuit Tracer prompt budget. gemma-2-2b caps the prompt at 64 tokens (a hard API
# limit; troubleshooting.md). We slide a token-accurate window over the context so that
# knowledge + prompt + generated output fit until the budget is reached, then the oldest
# (front) text glides off. No local tokenizer is available, so we estimate tokens from
# characters — robust to output tokens being concatenated without spaces (see the loop).
MAX_PROMPT_TOKENS = 64       # gemma-2-2b Circuit Tracer hard cap
PROMPT_TOKEN_BUDGET = 60     # usable budget; ~4 tokens headroom for server BOS/template tokens
CHARS_PER_TOKEN = 4          # ~chars per token for English gemma tokenization (approximate)

# Diff classification: a shared feature is amplified/suppressed by *relative* change in
# influence (scale-invariant), not an absolute delta. Control influences below the floor
# never meaningfully fired, so a present test feature there is treated as "added" rather
# than reported as a meaningless huge percentage.
AMPLIFY_THRESHOLD = 0.10   # ±10% relative change flips a shared feature to amplified/suppressed
INFLUENCE_FLOOR = 1e-3     # control influence below this is treated as absent


@dataclass
class Step:
    """One autoregressive step: a generated token and the attribution graph that produced it."""
    index: int
    token: str
    context_length: int
    attribution: dict = field(default_factory=dict)
    subgraph: dict | None = None

    def feature_ids(self) -> list[dict]:
        """Extract steering-ready feature identifiers from this step's subgraph."""
        if not self.subgraph or not self.subgraph.get("ok"):
            return []
        return [
            {"node_id": n["id"], "feature": n.get("feature"), "layer": n.get("layer"),
             "influence": n.get("influence", 0.0), "label": n.get("label", "")}
            for n in self.subgraph.get("nodes", [])
            if n.get("type") == "cross layer transcoder" and n.get("feature") is not None
        ]


@dataclass
class CompiledGraph:
    """The full autoregressive chain of attribution steps."""
    prompt: str
    system_prompt: str
    model: str
    steps: list[Step] = field(default_factory=list)

    @property
    def generated_text(self) -> str:
        return "".join(s.token for s in self.steps)

    @property
    def all_feature_ids(self) -> list[dict]:
        """All unique feature identifiers across all steps, for steering."""
        seen = set()
        out = []
        for step in self.steps:
            for f in step.feature_ids():
                key = (f["node_id"], f["layer"])
                if key not in seen:
                    seen.add(key)
                    out.append({**f, "step": step.index})
        return out

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "generated_text": self.generated_text,
            "steps": [asdict(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> CompiledGraph:
        return cls(
            prompt=d["prompt"],
            system_prompt=d.get("system_prompt", ""),
            model=d.get("model", "gemma-2-2b"),
            steps=[Step(**s) for s in d.get("steps", [])],
        )


def _node_key(node: dict) -> tuple:
    """Composite key for SAE-aligned node matching: (feature, depth, ctx_idx)."""
    return (node.get("feature"), node.get("depth"), node.get("ctx_idx"))


def _diff_subgraphs(ctrl_subgraph: dict | None, test_subgraph: dict | None) -> list[dict]:
    """Diff two subgraphs by SAE feature key.

    Returns a list of nodes annotated with `status`, `delta_influence` (absolute), and
    `rel_influence` (the signed relative change, or None when undefined). Shared features
    are classified by relative change so the threshold is scale-invariant: a feature is
    `amplified`/`suppressed` when test influence is ≥AMPLIFY_THRESHOLD above/below control.
    """
    ctrl_nodes = {}
    test_nodes = {}

    if ctrl_subgraph and ctrl_subgraph.get("ok"):
        for n in ctrl_subgraph.get("nodes", []):
            key = _node_key(n)
            if key != (None, None, None):
                ctrl_nodes[key] = n

    if test_subgraph and test_subgraph.get("ok"):
        for n in test_subgraph.get("nodes", []):
            key = _node_key(n)
            if key != (None, None, None):
                test_nodes[key] = n

    diff_nodes = []
    for key in set(ctrl_nodes.keys()) | set(test_nodes.keys()):
        ctrl_n = ctrl_nodes.get(key)
        test_n = test_nodes.get(key)

        if ctrl_n and not test_n:
            diff_nodes.append({**ctrl_n, "status": "removed", "delta_influence": 0.0,
                               "rel_influence": None})
        elif test_n and not ctrl_n:
            diff_nodes.append({**test_n, "status": "added", "delta_influence": 0.0,
                               "rel_influence": None})
        else:
            ctrl_inf = ctrl_n.get("influence", 0.0)
            test_inf = test_n.get("influence", 0.0)
            delta = test_inf - ctrl_inf

            if abs(ctrl_inf) < INFLUENCE_FLOOR:
                # Control never meaningfully fired: a present test feature is effectively new.
                if abs(test_inf) >= INFLUENCE_FLOOR:
                    status, rel = "added", None
                else:
                    status, rel = "unchanged", 0.0
            else:
                rel = delta / abs(ctrl_inf)
                if rel > AMPLIFY_THRESHOLD:
                    status = "amplified"
                elif rel < -AMPLIFY_THRESHOLD:
                    status = "suppressed"
                else:
                    status = "unchanged"

            diff_nodes.append({
                **test_n,
                "status": status,
                "delta_influence": round(delta, 4),
                "rel_influence": round(rel, 4) if rel is not None else None,
            })

    return diff_nodes


def diff_graphs(control: CompiledGraph, test: CompiledGraph) -> dict:
    """Diff step 0 of two compiled attribution graphs by SAE feature key.

    Only step 0 is meaningful: both chains see the same prompt (± knowledge layer)
    before autoregressive generation diverges their contexts. Comparing later steps
    would be incoherent since each chain generates different tokens.

    Returns {prompt, control_token, test_token, nodes: [{...node, status, delta_influence}]}.
    """
    ctrl_step = control.steps[0] if control.steps else None
    test_step = test.steps[0] if test.steps else None

    nodes = _diff_subgraphs(
        ctrl_step.subgraph if ctrl_step else None,
        test_step.subgraph if test_step else None,
    )

    return {
        "prompt": control.prompt,
        "control_token": ctrl_step.token if ctrl_step else "",
        "test_token": test_step.token if test_step else "",
        "nodes": nodes,
    }


def _sliding_window(text: str, budget_tokens: int = PROMPT_TOKEN_BUDGET) -> str:
    """Token-accurate gliding window for the Circuit Tracer's 64-token prompt cap.

    Keeps the most-recent ~budget_tokens of text (prompt tail + generated suffix + as much
    knowledge as fits). As output tokens are appended each step, the oldest front text glides
    off. Token count is estimated from characters (no local tokenizer; the Tracer tokenizes
    internally). The kept slice is snapped forward to the next word boundary so the window never
    begins mid-word, which would corrupt the leading token."""
    char_budget = budget_tokens * CHARS_PER_TOKEN
    if len(text) <= char_budget:
        return text
    tail = text[-char_budget:]
    # Snap forward to the next whitespace so we don't start in the middle of a word.
    space = tail.find(" ")
    if 0 <= space < len(tail) - 1:
        tail = tail[space + 1:]
    return tail.lstrip()


class AttributionLabelError(Exception):
    """Raised when Circuit Tracer returns a malformed or missing token label."""
    def __init__(self, reason: str, attrib: dict | None = None):
        self.reason = reason
        self.attrib = attrib
        super().__init__(reason)


def _extract_predicted_token(attrib: dict, subgraph: dict | None) -> str:
    """Extract the top predicted token from the attribution graph's logit nodes.

    Raises AttributionLabelError instead of silently returning '?'.
    """
    if subgraph and subgraph.get("ok"):
        logits = [n for n in subgraph.get("nodes", []) if n.get("is_target")]
        if logits:
            label = logits[0].get("label", "")
            import re
            m = re.match(r'^Output\s*"(.+?)"\s*\(p=', label)
            if m:
                return m.group(1)
            clean = label.replace("Output ", "").split(" (p=")[0].strip().strip('"')
            if clean:
                return clean
            raise AttributionLabelError(
                f"Logit node has unparseable label: {label!r}", attrib
            )
        raise AttributionLabelError(
            "Subgraph has no target logit nodes", attrib
        )

    if attrib.get("ok") and attrib.get("s3url"):
        raise AttributionLabelError(
            "Attribution graph OK but subgraph fetch failed or empty", attrib
        )
    raise AttributionLabelError(
        f"Attribution graph generation failed: {attrib.get('error', 'unknown')}", attrib
    )


def compile_attribution(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 10,
    on_step: Callable[[Step], None] | None = None,
) -> CompiledGraph:
    """Build a compiled attribution graph: autoregressive token generation with per-step causal graphs.

    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt / knowledge layer to prepend.
        max_tokens: Maximum number of autoregressive steps.
        on_step: Optional callback called after each step completes.

    Returns:
        CompiledGraph with the full chain of steps.
    """
    context = (system_prompt + "\n\n" + prompt).strip() if system_prompt else prompt
    graph = CompiledGraph(prompt=prompt, system_prompt=system_prompt, model="gemma-2-2b")

    for i in range(max_tokens):
        windowed = _sliding_window(context)

        attrib = npc.generate_attribution_graph(windowed)

        subgraph = None
        if attrib.get("ok") and attrib.get("s3url"):
            subgraph = npc.fetch_attribution_subgraph(
                attrib["s3url"], max_nodes=40, max_links=200
            )

        try:
            token = _extract_predicted_token(attrib, subgraph)
        except AttributionLabelError as e:
            step = Step(
                index=i, token="", context_length=len(context.split()),
                attribution=attrib, subgraph=subgraph,
            )
            step.error = e.reason
            graph.steps.append(step)
            if on_step:
                on_step(step)
            break

        step = Step(
            index=i,
            token=token,
            context_length=len(context.split()),
            attribution=attrib,
            subgraph=subgraph,
        )
        graph.steps.append(step)

        if on_step:
            on_step(step)

        context = context + token

    return graph
