"""Test that diff_graphs joins step-0 nodes by SAE feature key, not list position."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from borges_graph import CompiledGraph, Step, diff_graphs


def _make_graph(prompt, nodes, system_prompt=""):
    g = CompiledGraph(prompt=prompt, system_prompt=system_prompt, model="gemma-2-2b")
    g.steps.append(Step(
        index=0, token="t0", context_length=10,
        subgraph={"ok": True, "nodes": nodes, "links": []},
    ))
    return g


def test_diff_joins_by_sae_key_not_position():
    """Two graphs with the same features in DIFFERENT list order must match by key."""
    ctrl = _make_graph("test prompt", [
        {"id": "a", "feature": 100, "depth": 3, "ctx_idx": 5, "type": "cross layer transcoder",
         "influence": 0.8, "label": "feature A"},
        {"id": "b", "feature": 200, "depth": 4, "ctx_idx": 2, "type": "cross layer transcoder",
         "influence": 0.3, "label": "feature B"},
    ])

    test = _make_graph("test prompt", [
        {"id": "x", "feature": 200, "depth": 4, "ctx_idx": 2, "type": "cross layer transcoder",
         "influence": 0.9, "label": "feature B (test)"},
        {"id": "y", "feature": 100, "depth": 3, "ctx_idx": 5, "type": "cross layer transcoder",
         "influence": 0.8, "label": "feature A (test)"},
    ], system_prompt="knowledge layer")

    result = diff_graphs(ctrl, test)
    by_feature = {n["feature"]: n for n in result["nodes"]}

    assert by_feature[100]["status"] == "unchanged"
    assert by_feature[100]["delta_influence"] == 0.0
    assert by_feature[200]["status"] == "amplified"
    assert by_feature[200]["delta_influence"] == 0.6
    assert result["prompt"] == "test prompt"


def test_diff_detects_added_and_removed():
    ctrl = _make_graph("test", [
        {"id": "a", "feature": 100, "depth": 1, "ctx_idx": 0, "type": "cross layer transcoder",
         "influence": 0.5, "label": "only in control"},
    ])

    test = _make_graph("test", [
        {"id": "b", "feature": 200, "depth": 2, "ctx_idx": 1, "type": "cross layer transcoder",
         "influence": 0.7, "label": "only in test"},
    ], system_prompt="knowledge")

    result = diff_graphs(ctrl, test)
    statuses = {n["feature"]: n["status"] for n in result["nodes"]}

    assert statuses[100] == "removed"
    assert statuses[200] == "added"


def test_diff_returns_flat_structure():
    """Diff should return a flat dict with nodes, not a steps array."""
    ctrl = _make_graph("test", [
        {"id": "a", "feature": 1, "depth": 0, "ctx_idx": 0, "type": "cross layer transcoder",
         "influence": 0.5, "label": "f1"},
    ])
    test = _make_graph("test", [
        {"id": "b", "feature": 1, "depth": 0, "ctx_idx": 0, "type": "cross layer transcoder",
         "influence": 0.5, "label": "f1"},
    ], system_prompt="kl")

    result = diff_graphs(ctrl, test)
    assert "nodes" in result
    assert "steps" not in result
    assert "prompt" in result
    assert "control_token" in result
    assert "test_token" in result


if __name__ == "__main__":
    test_diff_joins_by_sae_key_not_position()
    test_diff_detects_added_and_removed()
    test_diff_returns_flat_structure()
    print("All diff_graphs tests passed.")
