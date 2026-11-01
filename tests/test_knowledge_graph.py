"""Test that the KG extractor reads prose into a pure sousConceptDe taxonomy."""

import re
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


EDGE_LINE = re.compile(r'^"([^"]+)" --sousConceptDe--> "([^"]+)"$')


def _labels(graph):
    return [n.label for n in graph.nodes]


def test_the_graph_is_the_test_arm_s_only_form():
    assert ks.TEST_ARM_FORM == "knowledge_graph"
    assert "knowledge_graph" in ks.STRUCTURE_FORMS


def test_the_rendering_is_nothing_but_subconcept_edges():
    """The form under test: a bare hierarchy of concepts, one relation, nothing else."""
    rendered = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    labels = {n.label for n in kg.extract_graph(KNOWLEDGE).nodes}
    lines = rendered.splitlines()
    assert lines
    for line in lines:
        match = EDGE_LINE.match(line)
        assert match, f"not a sousConceptDe edge: {line!r}"
        assert match.group(1) in labels and match.group(2) in labels
    assert len(set(lines)) == len(lines), "the same edge was printed twice"


def test_the_rendering_drops_the_sentences_on_purpose():
    """The taxonomy stands in for the prose — that is the trade this form makes."""
    rendered = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    assert not ks.preserves_claims(KNOWLEDGE, rendered)
    for claim in ks.split_claims(KNOWLEDGE):
        assert claim not in rendered


def test_every_edge_points_from_the_specific_to_the_general():
    graph = kg.extract_graph(KNOWLEDGE)
    assert kg.SUBCONCEPT_RELATION == "sousConceptDe"
    assert {e.relation for e in graph.edges} == {kg.SUBCONCEPT_RELATION}
    root = graph.nodes[0]
    ice = next(n for n in graph.nodes if n.label == "ice climbing")
    assert any(e.source == ice.id and e.target == root.id for e in graph.edges)
    assert not any(e.source == root.id and e.target == ice.id for e in graph.edges)


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
    """"It emerged in the Alps" hangs under Mountaineering, not under a node called "It"."""
    graph = kg.extract_graph(KNOWLEDGE)
    root = graph.nodes[0]
    assert root.label == "Mountaineering"
    alps = next(n for n in graph.nodes if n.label.startswith("Alps"))
    assert any(e.source == alps.id and e.target == root.id for e in graph.edges)
    assert not any(n.label.lower() in ("it", "its") for n in graph.nodes)


def test_a_possessive_pronoun_keeps_its_noun_and_takes_the_subject():
    graph = kg.extract_graph(KNOWLEDGE)
    assert "Mountaineering's principal hazards" in _labels(graph)


def test_a_list_wires_every_item_under_the_concept_it_hangs_off():
    graph = kg.extract_graph(KNOWLEDGE)
    root = graph.nodes[0].id
    under_root = {graph.node(e.source).label for e in graph.edges if e.target == root}
    assert {"rock climbing", "ice climbing", "ski touring"} <= under_root


def test_nodes_are_typed_off_their_labels():
    graph = kg.extract_graph("Everest is a mountain. It was first climbed in 1953. "
                             "It stands in the Himalaya.")
    kinds = {n.label: n.kind for n in graph.nodes}
    assert kinds["Everest"] == "entity"
    assert kinds["Himalaya"] == "entity"
    assert any(k == "value" for label, k in kinds.items() if "1953" in label)
    assert kinds["mountain"] == "concept"


def test_the_taxonomy_stays_connected_to_its_subject():
    """A claim with its own subject is still hung under the head subject."""
    graph = kg.extract_graph(KNOWLEDGE)
    root = graph.nodes[0].id
    parented = {e.source for e in graph.edges}
    orphans = [n.label for n in graph.nodes
               if n.id != root and n.id not in parented
               and any(e.target == n.id for e in graph.edges)]
    assert orphans == []


def test_targets_merge_onto_one_node_when_they_name_the_same_thing():
    """Two claims naming the same thing wire to one node — articles and case don't split it."""
    graph = kg.extract_graph("Alpinism includes ice climbing and ski touring. "
                             "It requires the Ice Climbing.")
    assert _labels(graph).count("ice climbing") == 1
    shared = next(n for n in graph.nodes if n.label == "ice climbing")
    assert len({e.claim_index for e in graph.edges if e.source == shared.id}) == 2


def test_empty_prose_yields_an_empty_rendering():
    assert ks.structure_knowledge("   ", "knowledge_graph") == ""
    assert kg.render_graph(kg.extract_graph("")) == ""


def test_stats_describe_the_taxonomy_the_setup_screen_shows():
    stats = kg.graph_stats(KNOWLEDGE)
    assert stats["subject"] == "Mountaineering"
    assert stats["n_nodes"] > 0 and stats["n_edges"] > 0
    assert stats["relations"] == {"sousConceptDe": stats["n_edges"]}
    assert sum(stats["node_kinds"].values()) == stats["n_nodes"]
    # False by design: the edge list is the whole rendering, the sentences stay behind.
    assert stats["claims_preserved"] is False


def test_structure_stats_carries_the_graph_for_the_graph_form():
    stats = ks.structure_stats(KNOWLEDGE, "knowledge_graph")
    assert stats["form_label"] == "Knowledge graph"
    assert stats["graph"]["n_edges"] == len(kg.extract_graph(KNOWLEDGE).edges)
    # No other form carries one.
    assert "graph" not in ks.structure_stats(KNOWLEDGE, "prose")


def test_payload_is_plain_json_shaped():
    payload = kg.graph_payload(KNOWLEDGE)
    assert set(payload) == {"source", "model", "fallbackReason",
                            "subject", "aliases", "nodes", "edges"}
    # With no key in the environment the rule-based reader is what ran, and says why.
    assert payload["source"] == "rules"
    assert "OPENROUTER_API_KEY" in payload["fallbackReason"]
    assert set(payload["nodes"][0]) == {"id", "label", "kind"}
    assert set(payload["edges"][0]) == {"source", "relation", "target", "claimIndex"}


def test_extraction_is_deterministic():
    """No model call, no network — the same prose always renders the same graph."""
    first = ks.structure_knowledge(KNOWLEDGE, "knowledge_graph")
    assert all(ks.structure_knowledge(KNOWLEDGE, "knowledge_graph") == first for _ in range(3))
