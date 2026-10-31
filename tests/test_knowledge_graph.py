"""Test that the KG extractor reads prose into a graph without rewriting a single claim."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import knowledge_graph as kg
import knowledge_structurer as ks


KNOWLEDGE = (
    "Mountaineering (alpinism) is the set of sporting activities that involve ascending "
    "mountains, including rock climbing, ice climbing and ski touring. It emerged in the "
    "Alps in the 18th century; it is governed today by national alpine federations. "
    "Its principal hazards are avalanches, rockfall and altitude sickness."
)


def _labels(graph):
    return [n.label for n in graph.nodes]


def test_the_graph_is_the_test_arm_s_only_form():
    assert ks.TEST_ARM_FORM == "knowledge_graph"
    assert "knowledge_graph" in ks.STRUCTURE_FORMS


def test_every_claim_survives_verbatim_in_the_rendered_graph():
    """The whole experiment rests on this: the graph is laid over the facts, not instead of them."""
    rendered = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    for claim in ks.split_claims(KNOWLEDGE):
        assert claim in rendered, f"the graph dropped or rewrote: {claim!r}"
    assert ks.preserves_claims(KNOWLEDGE, rendered)


def test_every_claim_contributes_at_least_one_edge():
    graph = kg.extract_graph(KNOWLEDGE)
    by_claim = graph.edges_by_claim()
    for claim in graph.claims:
        assert by_claim.get(claim.index), f"claim {claim.index} entered the graph mute"


def test_a_cue_at_the_very_end_of_a_claim_still_yields_an_edge():
    """"… is its conventional starting point" leaves no object span to the cue's right."""
    text = ("Mountaineering is a sport. The 1786 ascent of Mont Blanc by Jacques Balmat "
            "is its conventional starting point.")
    graph = kg.extract_graph(text)
    assert graph.edges_by_claim().get(1), "a trailing cue swallowed the claim"


def test_the_head_subject_is_a_single_node_aliases_and_all():
    """"Mountaineering (alpinism)" must not split off from "Mountaineering"."""
    graph = kg.extract_graph(KNOWLEDGE)
    assert graph.subject == "Mountaineering"
    assert graph.aliases == ["alpinism"]
    assert _labels(graph).count("Mountaineering") == 1
    assert "Mountaineering (alpinism)" not in _labels(graph)


def test_bare_pronouns_resolve_back_to_the_head_subject():
    """"It emerged in the Alps" hangs off Mountaineering, not off a node called "It"."""
    graph = kg.extract_graph(KNOWLEDGE)
    root = graph.nodes[0]
    assert root.label == "Mountaineering"
    origin = next(e for e in graph.edges if e.relation == "origin")
    assert origin.source == root.id
    assert not any(n.label.lower() in ("it", "its") for n in graph.nodes)


def test_a_possessive_pronoun_keeps_its_noun_and_takes_the_subject():
    graph = kg.extract_graph(KNOWLEDGE)
    assert "Mountaineering's principal hazards" in _labels(graph)


def test_a_list_hangs_off_its_claim_as_composition():
    graph = kg.extract_graph(KNOWLEDGE)
    composed = {graph.node(e.target).label for e in graph.edges if e.relation == "composition"}
    assert {"rock climbing", "ice climbing", "ski touring"} <= composed


def test_nodes_are_typed_off_their_labels():
    graph = kg.extract_graph("Everest is a mountain. It was first climbed in 1953. "
                             "It stands in the Himalaya.")
    kinds = {n.label: n.kind for n in graph.nodes}
    assert kinds["Everest"] == "entity"
    assert kinds["Himalaya"] == "entity"
    assert any(k == "value" for label, k in kinds.items() if "1953" in label)
    assert kinds["mountain"] == "concept"


def test_the_graph_stays_connected_to_its_subject():
    """A claim with its own subject is still attached to the head subject."""
    graph = kg.extract_graph(KNOWLEDGE)
    root = graph.nodes[0].id
    incoming = {e.target for e in graph.edges}
    orphans = [n.label for n in graph.nodes
               if n.id != root and n.id not in incoming
               and any(e.source == n.id for e in graph.edges)]
    assert orphans == []


def test_targets_merge_onto_one_node_when_they_name_the_same_thing():
    """Two claims naming the same thing wire to one node — articles and case don't split it."""
    graph = kg.extract_graph("Alpinism includes ice climbing and ski touring. "
                             "It requires the Ice Climbing.")
    assert _labels(graph).count("ice climbing") == 1
    shared = next(n for n in graph.nodes if n.label == "ice climbing")
    assert len({e.claim_index for e in graph.edges if e.target == shared.id}) == 2


def test_empty_prose_yields_an_empty_rendering():
    assert ks.structure_knowledge("   ", "knowledge_graph") == ""
    assert kg.render_graph(kg.extract_graph("")) == ""


def test_rendering_names_its_nodes_before_it_wires_them():
    rendered = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    assert rendered.splitlines()[0] == "knowledge graph: Mountaineering"
    assert rendered.index("\nNODES") < rendered.index("\nEDGES")
    # Every edge references declared node ids.
    ids = {n.id for n in kg.extract_graph(KNOWLEDGE).nodes}
    for line in rendered.splitlines():
        stripped = line.strip()
        if "-[" in stripped and "]->" in stripped:
            source, target = stripped.split(" -[")[0], stripped.split("]-> ")[1]
            assert source in ids and target in ids


def test_stats_describe_the_graph_the_setup_screen_shows():
    stats = kg.graph_stats(KNOWLEDGE)
    assert stats["subject"] == "Mountaineering"
    assert stats["n_nodes"] > 0 and stats["n_edges"] > 0
    assert sum(stats["relations"].values()) == stats["n_edges"]
    assert sum(stats["node_kinds"].values()) == stats["n_nodes"]
    assert stats["claims_preserved"] is True


def test_structure_stats_carries_the_graph_for_the_graph_form():
    stats = ks.structure_stats(KNOWLEDGE, "knowledge_graph")
    assert stats["form_label"] == "Knowledge graph"
    assert stats["graph"]["n_edges"] == len(kg.extract_graph(KNOWLEDGE).edges)
    # No other form carries one.
    assert "graph" not in ks.structure_stats(KNOWLEDGE, "prose")


def test_payload_is_plain_json_shaped():
    payload = kg.graph_payload(KNOWLEDGE)
    assert set(payload) == {"subject", "aliases", "nodes", "edges"}
    assert set(payload["nodes"][0]) == {"id", "label", "kind"}
    assert set(payload["edges"][0]) == {"source", "relation", "target", "claimIndex"}


def test_extraction_is_deterministic():
    """No model call, no network — the same prose always renders the same graph."""
    first = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    assert all(ks.structure_knowledge(KNOWLEDGE, "knowledge_graph") == first for _ in range(3))
