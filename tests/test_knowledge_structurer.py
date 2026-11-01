"""Test that the structurer re-arranges a knowledge layer without rewriting its facts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import knowledge_structurer as ks


KNOWLEDGE = (
    "Mountaineering (alpinism) is the set of sporting activities that involve ascending "
    "mountains. It emerged in the Alps in the 18th century; it is governed today by national "
    "alpine federations. Its principal hazards are avalanches and altitude sickness."
)


def test_every_claim_survives_verbatim_in_every_prose_carrying_form():
    """Only the form changes, never the facts — for every form that still carries prose."""
    claims = ks.split_claims(KNOWLEDGE)
    assert len(claims) == 4

    for form in ks.STRUCTURE_FORMS:
        if form == "knowledge_graph":
            continue   # the taxonomy is edges only — see test_knowledge_graph.py
        rendered = ks.structure_knowledge(KNOWLEDGE, form)
        for claim in claims:
            assert claim in rendered, f"{form} dropped or rewrote: {claim!r}"


def test_the_knowledge_graph_form_is_the_one_that_leaves_the_prose_behind():
    """The test arm's form renders a bare sousConceptDe taxonomy, not the sentences."""
    rendered = ks.structure_knowledge(KNOWLEDGE, ks.TEST_ARM_FORM)
    assert not ks.preserves_claims(KNOWLEDGE, rendered)
    assert all(" --sousConceptDe--> " in line for line in rendered.splitlines())


def test_semicolons_split_into_separate_claims():
    claims = ks.split_claims("It emerged in the Alps; it is governed by federations.")
    assert claims == ["It emerged in the Alps", "it is governed by federations."]


def test_fragments_below_the_floor_are_not_claims():
    assert ks.split_claims("Yes. Mountaineering is a sport practised in the Alps.") == [
        "Mountaineering is a sport practised in the Alps."
    ]


def test_relation_is_the_cue_that_appears_earliest():
    # "is the set of" (definition) precedes "involve" (requirement) and "including".
    assert ks.classify_claim(
        "Mountaineering is the set of activities that involve ascending mountains, "
        "including ice climbing") == "definition"
    # A passive "is governed" must not be read as a copular definition.
    assert ks.classify_claim("It is governed today by alpine federations.") == "governance"
    assert ks.classify_claim("Its principal hazards are avalanches.") == "risk"


def test_claims_with_no_cue_fall_back_to_property():
    assert ks.classify_claim("The rope weighed on his shoulder all afternoon.") == "property"


def test_subject_and_aliases_come_from_the_first_claim():
    subject, aliases = ks.extract_subject(ks.split_claims(KNOWLEDGE))
    assert subject == "Mountaineering"
    assert aliases == ["alpinism"]


def test_schema_groups_claims_under_relation_keys():
    rendered = ks.structure_knowledge(KNOWLEDGE, "schema")
    assert rendered.startswith("entity: Mountaineering")
    assert "aliases: alpinism" in rendered
    assert "definition:" in rendered and "risk:" in rendered


def test_typed_facts_emits_one_triple_per_claim():
    rendered = ks.structure_knowledge(KNOWLEDGE, "typed_facts")
    triples = [l for l in rendered.splitlines() if l.count(" | ") == 2 and not l.startswith("subject |")]
    assert len(triples) == len(ks.split_claims(KNOWLEDGE))
    assert all(l.startswith("Mountaineering | ") for l in triples)


def test_prose_is_the_untouched_baseline():
    assert ks.structure_knowledge(KNOWLEDGE, "prose") == KNOWLEDGE.strip()


def test_empty_knowledge_renders_empty_in_every_form():
    for form in ks.STRUCTURE_FORMS:
        assert ks.structure_knowledge("   ", form) == ""


def test_unknown_form_is_rejected():
    with pytest.raises(ValueError, match="Unknown structure form"):
        ks.structure_knowledge(KNOWLEDGE, "ontology")


def test_stats_describe_what_the_structurer_saw():
    stats = ks.structure_stats(KNOWLEDGE, "schema")
    assert stats["n_claims"] == 4
    assert stats["subject"] == "Mountaineering"
    assert stats["claims_preserved"] is True
    assert sum(stats["relations"].values()) == 4
