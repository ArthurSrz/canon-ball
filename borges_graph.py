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
    - NLA verbalization runs on different models (gemma-3-27b, llama-3.3-70b) — not used here
    - Feature identifiers (SAE dictionary indices) are preserved for future steering
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable

import neuronpedia_client as npc


WINDOW_SIZE = 60


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


def _sliding_window(text: str, max_tokens: int = WINDOW_SIZE) -> str:
    """Approximate sliding window by keeping the last ~max_tokens words.
    The Circuit Tracer tokenizes internally, so we estimate by whitespace."""
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[-max_tokens:])


def _extract_predicted_token(attrib: dict, subgraph: dict | None) -> str:
    """Extract the top predicted token from the attribution graph's logit nodes."""
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

    if attrib.get("ok") and attrib.get("s3url"):
        return "?"
    return "?"


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

        token = _extract_predicted_token(attrib, subgraph)

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

        if token == "?":
            break

        context = context + token

    return graph
