"""Test the two LLM extraction passes — the parsing, the rules they are held to, and the
fallback that keeps the instrument working with no key and no network.

The model is stubbed throughout. These tests pin down what this module does with a reply,
not what any model actually replies; nothing here stands in for a real extraction.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import concept_extractor as ce
import knowledge_graph as kg


KNOWLEDGE = (
    "Mountaineering (alpinism) is the set of sporting activities that involve ascending "
    "mountains, including rock climbing, ice climbing and ski touring. It emerged in the "
    "Alps in the 18th century; it is governed today by national alpine federations. "
    "Its principal hazards are avalanches, rockfall and altitude sickness."
)

CONCEPTS_REPLY = {
    "subject": "Mountaineering",
    "concepts": ["Mountaineering", "rock climbing", "ice climbing", "ski touring",
                 "alpine federations", "avalanches", "rockfall", "altitude sickness",
                 "principal hazards"],
}

LINKS_REPLY = {
    "links": [
        ["rock climbing", "Mountaineering"],
        ["ice climbing", "Mountaineering"],
        ["ski touring", "Mountaineering"],
        ["principal hazards", "Mountaineering"],
        ["avalanches", "principal hazards"],
        ["rockfall", "principal hazards"],
        ["altitude sickness", "principal hazards"],
    ]
}


@pytest.fixture(autouse=True)
def _clean_cache():
    ce.clear_cache()
    yield
    ce.clear_cache()


@pytest.fixture
def stub_model(monkeypatch):
    """Answer pass 1 and pass 2 from canned replies, and count the calls."""
    calls = []

    def fake_chat(prompt, model, max_tokens):
        calls.append(prompt)
        return CONCEPTS_REPLY if "CONCEPTS:" not in prompt else LINKS_REPLY

    monkeypatch.setattr(ce, "_openrouter_key", lambda: "test-key")
    monkeypatch.setattr(ce, "_chat_json", fake_chat)
    return calls


# ───────────────────────────── reply parsing ─────────────────────────────

def test_json_is_read_through_fences_and_preamble():
    assert ce._parse_json('{"a": 1}') == {"a": 1}
    assert ce._parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ce._parse_json('Sure, here you go:\n{"a": 1}') == {"a": 1}
    with pytest.raises(ValueError, match="no JSON"):
        ce._parse_json("I cannot do that.")


def test_pass_one_dedupes_and_trims_what_it_is_handed(monkeypatch):
    monkeypatch.setattr(ce, "_chat_json", lambda *a: {
        "subject": "The Mountaineering",
        "concepts": ["Mountaineering", "  ice climbing  ", "Ice Climbing", "the Alps"],
    })
    subject, concepts = ce.extract_concepts(KNOWLEDGE, "stub")
    assert subject == "Mountaineering"
    assert concepts == ["Mountaineering", "ice climbing", "Alps"]


def test_pass_one_refuses_a_reply_that_names_nothing(monkeypatch):
    monkeypatch.setattr(ce, "_chat_json", lambda *a: {"subject": "", "concepts": []})
    with pytest.raises(ValueError, match="named no concepts"):
        ce.extract_concepts(KNOWLEDGE, "stub")


def test_pass_two_accepts_pairs_or_objects(monkeypatch):
    monkeypatch.setattr(ce, "_chat_json", lambda *a: {
        "links": [["a", "b"], {"child": "c", "parent": "d"}, "junk"],
    })
    assert ce.extract_links(KNOWLEDGE, "b", ["a", "b", "c", "d"], "stub") == [
        ("a", "b"), ("c", "d")
    ]


# ───────────────────────────── the rules pass 2 is held to ─────────────────────────────

def test_a_link_naming_a_concept_that_was_never_extracted_is_dropped():
    """Drift, not discovery: pass 2 may only wire what pass 1 named."""
    links = ce.resolve_links([("rock climbing", "Sport")], "Mountaineering",
                             ["Mountaineering", "rock climbing"])
    assert ("rock climbing", "Sport") not in links


def test_self_links_and_links_onto_the_root_are_dropped():
    links = ce.resolve_links(
        [("Mountaineering", "rock climbing"), ("rock climbing", "rock climbing")],
        "Mountaineering", ["Mountaineering", "rock climbing"],
    )
    assert ("Mountaineering", "rock climbing") not in links
    assert ("rock climbing", "rock climbing") not in links


def test_a_link_that_would_close_a_cycle_is_dropped():
    concepts = ["Root", "A", "B"]
    links = ce.resolve_links([("A", "B"), ("B", "A")], "Root", concepts)
    assert ("A", "B") in links
    assert ("B", "A") not in links


def test_a_concept_left_floating_is_hung_off_the_root():
    concepts = ["Mountaineering", "rock climbing", "ski touring"]
    links = ce.resolve_links([("rock climbing", "Mountaineering")], "Mountaineering",
                             concepts)
    assert ("ski touring", "Mountaineering") in links


def test_matching_back_to_a_concept_ignores_case_and_articles():
    links = ce.resolve_links([("The Rock Climbing", "mountaineering")], "Mountaineering",
                             ["Mountaineering", "rock climbing"])
    assert links == [("rock climbing", "Mountaineering")]


# ───────────────────────────── the two passes together ─────────────────────────────

def test_both_passes_run_and_the_second_is_handed_the_first_s_concepts(stub_model):
    extraction = ce.extract(KNOWLEDGE)
    assert extraction is not None
    assert len(stub_model) == 2
    assert "CONCEPTS:" in stub_model[1] and "- ice climbing" in stub_model[1]
    assert extraction.subject == "Mountaineering"
    assert ("avalanches", "principal hazards") in extraction.links


def test_an_extraction_is_cached_so_a_preview_does_not_refire_it(stub_model):
    first = ce.extract(KNOWLEDGE)
    assert ce.extract(KNOWLEDGE) is first
    assert len(stub_model) == 2, "the second preview hit the model again"


def test_no_key_means_no_llm_call_and_a_stated_reason(monkeypatch):
    monkeypatch.setattr(ce, "_openrouter_key", lambda: "")
    monkeypatch.setattr(ce, "_chat_json", lambda *a: pytest.fail("called with no key"))
    assert ce.extract(KNOWLEDGE) is None
    assert "OPENROUTER_API_KEY" in ce.last_failure()


def test_a_reply_that_is_not_json_falls_back_instead_of_raising(monkeypatch):
    monkeypatch.setattr(ce, "_openrouter_key", lambda: "test-key")
    monkeypatch.setattr(ce, "_chat_json",
                        lambda *a: (_ for _ in ()).throw(ValueError("no JSON in reply")))
    assert ce.extract(KNOWLEDGE) is None
    assert "no JSON" in ce.last_failure()


def test_the_model_is_configurable_and_defaults_to_the_documented_slug(monkeypatch):
    monkeypatch.delenv("KS_EXTRACTION_MODEL", raising=False)
    assert ce.extraction_model() == ce.DEFAULT_EXTRACTION_MODEL
    monkeypatch.setenv("KS_EXTRACTION_MODEL", "vendor/some-model")
    assert ce.extraction_model() == "vendor/some-model"


# ───────────────────────────── what the graph does with it ─────────────────────────────

def test_the_graph_is_built_from_the_extraction_and_says_so(stub_model):
    graph = kg.extract_graph(KNOWLEDGE)
    assert graph.source == "llm"
    assert graph.model == ce.extraction_model()
    assert {e.relation for e in graph.edges} == {kg.SUBCONCEPT_RELATION}
    labels = {n.label for n in graph.nodes}
    assert {"Mountaineering", "rock climbing", "principal hazards"} <= labels


def test_the_llm_graph_still_renders_as_nothing_but_subconcept_edges(stub_model):
    rendered = kg.render_graph(kg.extract_graph(KNOWLEDGE))
    assert rendered
    for line in rendered.splitlines():
        assert line.startswith('"') and ' --sousConceptDe--> ' in line


def test_every_edge_is_grounded_in_a_claim_the_hover_can_print(stub_model):
    graph = kg.extract_graph(KNOWLEDGE)
    indexes = {c.index for c in graph.claims}
    assert all(e.claim_index in indexes for e in graph.edges)


def test_without_the_llm_the_graph_falls_back_to_the_rules_and_says_so(monkeypatch):
    monkeypatch.setattr(ce, "extract", lambda text: None)
    graph = kg.extract_graph(KNOWLEDGE)
    assert graph.source == "rules"
    assert graph.edges and {e.relation for e in graph.edges} == {kg.SUBCONCEPT_RELATION}
