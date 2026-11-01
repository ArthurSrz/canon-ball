"""
Canon Ball Knowledge Graph Extractor
Reads a free-prose knowledge layer into a *taxonomy*: concepts, and one single relation
between them — subsumption.

The extracted layer is composed of nothing but lines of the shape

    "Concept A" --sousConceptDe--> "Concept B"

read as *A is a sub-concept of B*: the arrow runs from the specific to the general. There
is no header, no node table, and no prose — the rendering is the edge list and nothing
else. That is the whole point of the form: the test arm is loaded with a bare hierarchy of
concepts, so what the volley measures is what a *taxonomy* does to the model, stripped of
every sentence it was read from.

Deterministic — no model call, no network. The same prose always yields the same taxonomy,
which is what lets a volley fired at `knowledge_graph` be compared with one fired at
`prose`.

Note the trade this form makes: because the rendering drops the sentences, the claims are
NOT carried through verbatim (`preserves_claims` is False for this form, by design, and
`graph_stats` reports it honestly). The facts reach the model only as the concepts the
extractor named and the hierarchy it read between them.

Two readers produce that taxonomy, and `extract_graph` picks between them:

  * **The LLM reader** (`concept_extractor.py`, the default). Two passes against a
    frontier model: pass 1 names the concepts, pass 2 is handed only those concepts and
    says which sits under which. `graph.source == "llm"`.
  * **The rule-based reader** (this module, the fallback). Cuts the prose into claims
    (knowledge_structurer), reads each claim's cue to find its head concept and the
    concepts hanging off it, and wires each of those as a sub-concept of the head. The
    relation cues drive the *parsing* only — they no longer type the edges, because every
    edge carries the one relation. `graph.source == "rules"`.

The fallback runs whenever the LLM path cannot: no `OPENROUTER_API_KEY`, an unreachable
host, or a reply that is not the JSON that was asked for. It is deterministic and needs no
network, which is what keeps the test suite and `--dry-run` working offline. `graph.source`
and `graph_stats()["source"]` always say which one ran, so a result is never read as
model-extracted when the rules produced it.

    extract_graph(text) -> KnowledgeGraph
    render_graph(graph) -> str          the knowledge-layer rendering fired at the model
    graph_stats(text)   -> dict         counts for the setup screen and the report
"""

import re
from dataclasses import dataclass, field

import concept_extractor as ce
import knowledge_structurer as ks


# Opens a list of objects rather than naming one. A target read after one of these
# hangs off its claim as `composition`, whatever the claim's own relation is.
LIST_CUES = re.compile(
    r"^(?:including|includes?|such as|like|namely|e\.g\.|for example|both|all of them)\b[,:]?\s*",
    re.IGNORECASE,
)

# Grammar, not content, when it opens an object span. Stripped repeatedly.
LEADING_NOISE = re.compile(
    r"^(?:and|or|also|then|today|nowadays|now|by|to|for|of|in|on|from|with|as|at|that|which"
    r"|who|where|when|while|whose|it|its|is|are|was|were|be|been|being|has|have|had)\s+",
    re.IGNORECASE,
)

LEADING_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)

# An alias in parentheses belongs in the header, not in a node label — and leaving it in
# would split "Mountaineering (alpinism)" off from "Mountaineering" as a second node.
PARENTHETICAL = re.compile(r"\s*\([^)]*\)")

# A claim that opens on one of these opens on a circumstance, not on a subject, so the
# claim hangs off the head subject instead: "Above roughly 8000 m climbers enter …".
CIRCUMSTANTIAL_HEAD = re.compile(
    r"^(?:above|below|beyond|under|over|during|since|until|within|across|among|between"
    r"|after|before|because|although|though|however|roughly|about|approximately|nearly"
    r"|today|nowadays|in|on|at|from|by|with|for|to|as|when|while|where|if|so|thus"
    r"|therefore|also|and|but)\b",
    re.IGNORECASE,
)

# Relations whose cue is a noun inside the subject phrase ("its principal HAZARDS are …",
# "fourteen peaks exceed 8000 M"), not a predicate. The cue stays on the source side.
SOURCE_INCLUDES_CUE = {"risk", "measure"}

# Relations whose cue swallows the thing it points at ("IN THE HIMALAYA", "IN 1953").
# The match itself is the target; without this the place or the date never reaches a node.
CUE_IS_OBJECT = {"location", "time"}

# Relations whose cue enumerates, so "X and Y" after it is two things, not one
# ("includes ice climbing and ski touring", "hazards are avalanches and rockfall").
SPLIT_FIRST_SEGMENT = {"composition", "risk", "requirement"}

# "It emerged in the Alps", "It stands in the Himalaya" — a claim that opens on a pronoun
# is a claim about the head subject, whatever predicate follows the pronoun.
BARE_PRONOUN = re.compile(r"^(?:it|they|he|she|this|these|those)\b", re.IGNORECASE)
# "Its principal hazards are …" — the pronoun is possessive, so the subject takes its place.
POSSESSIVE = re.compile(r"^(?:its|their|his|her)\s+", re.IGNORECASE)

EDGE_PREFIX = "n"
MIN_NODE_CHARS = 3
MAX_NODE_LABEL_CHARS = 80
MAX_TARGETS_PER_CLAIM = 6

# The only relation the extracted taxonomy carries. Read "A --sousConceptDe--> B"
# as *A is a sub-concept of B*: the arrow runs specific → general.
SUBCONCEPT_RELATION = "sousConceptDe"


@dataclass
class Node:
    """One thing the graph names. `kind` is read off the label, not supplied."""
    id: str
    label: str
    kind: str


@dataclass
class Edge:
    """A typed link, carrying the index of the claim it was read from."""
    source: str
    relation: str
    target: str
    claim_index: int


@dataclass
class KnowledgeGraph:
    subject: str
    aliases: list[str] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    claims: list[ks.Claim] = field(default_factory=list)
    # Which reader produced this — "llm" or "rules". Never inferred by a caller.
    source: str = "rules"
    model: str = ""

    def node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def edges_by_claim(self) -> dict[int, list[Edge]]:
        """Edges grouped under the claim they came from, in claim order."""
        grouped: dict[int, list[Edge]] = {}
        for edge in self.edges:
            grouped.setdefault(edge.claim_index, []).append(edge)
        return grouped

    def relations(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for edge in self.edges:
            counts[edge.relation] = counts.get(edge.relation, 0) + 1
        return counts

    def node_kinds(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.kind] = counts.get(node.kind, 0) + 1
        return counts


def _clean_span(span: str) -> str:
    """Trim a raw span down to a node label: no list cue, no leading grammar, no article."""
    span = PARENTHETICAL.sub("", span)
    span = span.strip().strip(" \t,;:.—–-")
    span = LIST_CUES.sub("", span)
    previous = None
    while previous != span:
        previous = span
        span = LEADING_NOISE.sub("", span).lstrip()
    span = LEADING_ARTICLE.sub("", span)
    span = re.sub(r"\s+", " ", span).strip(" \t,;:.—–-")
    if len(span) > MAX_NODE_LABEL_CHARS:
        span = span[:MAX_NODE_LABEL_CHARS].rsplit(" ", 1)[0] + "…"
    return span


def _merge_key(label: str) -> str:
    """Two spans naming the same thing collapse onto one node."""
    key = LEADING_ARTICLE.sub("", label.lower().strip())
    return re.sub(r"[^a-z0-9 ]", "", key).strip()


def _kind(label: str, is_root: bool = False) -> str:
    """Type a node off its label: the head subject is an entity, a figure is a value."""
    if is_root:
        return "entity"
    if re.search(r"\d", label):
        return "value"
    head = label.split()[0] if label.split() else ""
    return "entity" if head[:1].isupper() else "concept"


def _claim_source(head: str, subject: str) -> str:
    """The span a claim hangs off — with pronouns resolved back to the head subject."""
    head = PARENTHETICAL.sub("", head).strip().strip(" \t,;:.—–-")
    head = LEADING_ARTICLE.sub("", head)

    if not head:
        return subject or "subject"
    if BARE_PRONOUN.match(head):
        return subject or head
    if POSSESSIVE.match(head):
        return (f"{subject}'s {POSSESSIVE.sub('', head)}".strip() if subject
                else POSSESSIVE.sub("", head))
    if CIRCUMSTANTIAL_HEAD.match(head) and subject:
        return subject
    return head


def _split_targets(tail: str, split_first: bool = False) -> list[str]:
    """Cut an object span into the concepts it names.

    The first comma-segment is kept whole — "sporting and leisure activities" is one
    thing, not two. Later segments are split on "and", because that is where prose
    actually enumerates. `split_first` lifts that guard for a claim whose own cue already
    enumerates ("includes ice climbing and ski touring").
    """
    targets: list[str] = []
    in_list = False

    for position, segment in enumerate(s for s in re.split(r",\s*", tail) if s.strip()):
        if LIST_CUES.search(segment.strip()):
            in_list = True
        splits = position > 0 or in_list or split_first
        parts = re.split(r"\s+and\s+", segment) if splits else [segment]
        for part in parts:
            label = _clean_span(part)
            if len(label) >= MIN_NODE_CHARS:
                targets.append(label)

    return targets[:MAX_TARGETS_PER_CLAIM]


def extract_graph(text: str) -> KnowledgeGraph:
    """Read prose into a taxonomy, by LLM where possible and by rule where not."""
    extraction = ce.extract(text)
    if extraction is not None and extraction.links:
        return _graph_from_extraction(text, extraction)
    return _graph_from_rules(text)


def _graph_from_extraction(text: str, extraction: ce.Extraction) -> KnowledgeGraph:
    """Build the taxonomy from what the two LLM passes named."""
    knowledge = ks.analyze_knowledge(text)
    graph = KnowledgeGraph(
        subject=extraction.subject,
        aliases=knowledge.aliases,
        claims=knowledge.claims,
        source="llm",
        model=extraction.model,
    )

    index: dict[str, str] = {}

    def node_id(label: str, is_root: bool = False) -> str:
        key = _merge_key(label)
        if key in index:
            return index[key]
        new_id = f"{EDGE_PREFIX}{len(graph.nodes)}"
        graph.nodes.append(Node(id=new_id, label=label, kind=_kind(label, is_root)))
        index[key] = new_id
        return new_id

    node_id(extraction.subject, is_root=True)
    for concept in extraction.concepts:
        node_id(concept)

    for child, parent in extraction.links:
        child_id, parent_id = node_id(child), node_id(parent)
        if child_id == parent_id:
            continue
        graph.edges.append(Edge(
            source=child_id,
            relation=SUBCONCEPT_RELATION,
            target=parent_id,
            claim_index=_claim_for(child, parent, knowledge.claims),
        ))

    return graph


def _claim_for(child: str, parent: str, claims: list[ks.Claim]) -> int:
    """The sentence a link is most likely to have come from.

    Best-effort grounding, not the model's own attribution: the passes are not asked which
    sentence a link came from, so this is a lookup over the claims the structurer already
    cut. It exists so hovering an edge in the graph view still prints a sentence to check
    the link against.
    """
    for needle in (child, parent):
        lowered = needle.casefold()
        for claim in claims:
            if lowered in claim.text.casefold():
                return claim.index
    return claims[0].index if claims else 0


def _graph_from_rules(text: str) -> KnowledgeGraph:
    """The deterministic fallback. Every claim contributes at least one sousConceptDe edge."""
    knowledge = ks.analyze_knowledge(text)
    graph = KnowledgeGraph(
        subject=knowledge.subject,
        aliases=knowledge.aliases,
        claims=knowledge.claims,
    )

    index: dict[str, str] = {}

    def node_id(label: str, is_root: bool = False) -> str:
        key = _merge_key(label)
        if key in index:
            return index[key]
        new_id = f"{EDGE_PREFIX}{len(graph.nodes)}"
        graph.nodes.append(Node(id=new_id, label=label, kind=_kind(label, is_root)))
        index[key] = new_id
        return new_id

    if knowledge.subject:
        node_id(knowledge.subject, is_root=True)

    for claim in knowledge.claims:
        relation, match = ks.match_relation(claim.text)
        if match:
            cut = match.end() if relation in SOURCE_INCLUDES_CUE else match.start()
            head_raw, tail = claim.text[:cut], claim.text[match.end():]
        else:
            head_raw, tail = "", claim.text

        source_label = _clean_span(_claim_source(head_raw, knowledge.subject))
        targets = _split_targets(tail, split_first=relation in SPLIT_FIRST_SEGMENT)
        if match and relation in CUE_IS_OBJECT:
            cued = _clean_span(match.group(0))
            if len(cued) >= MIN_NODE_CHARS:
                targets.insert(0, cued)

        # A cue sitting at the end of a claim ("… is its conventional starting point")
        # leaves no object span. The thing the claim names is then on the cue's left, so
        # the claim hangs off the head subject instead — no claim enters the graph mute.
        if not targets:
            fallback = _clean_span(head_raw) or _clean_span(claim.text)
            targets = [fallback or claim.text[:MAX_NODE_LABEL_CHARS]]
            source_label = knowledge.subject or source_label

        if len(source_label) < MIN_NODE_CHARS:
            source_label = knowledge.subject or claim.text[:MAX_NODE_LABEL_CHARS]
        parent = node_id(source_label, is_root=source_label == knowledge.subject)

        # A claim's own subject ("its principal hazards") is itself a sub-concept of the
        # head subject, so the taxonomy stays one tree rather than a scatter of little
        # stars. Only wired when that concept has no parent of its own yet.
        root = index.get(_merge_key(knowledge.subject)) if knowledge.subject else None
        if root and parent != root and not any(e.source == parent for e in graph.edges):
            graph.edges.append(Edge(source=parent, relation=SUBCONCEPT_RELATION,
                                    target=root, claim_index=claim.index))

        # Everything the claim hangs off its head is a sub-concept of that head.
        for label in targets:
            child = node_id(label)
            if child == parent:
                continue
            graph.edges.append(Edge(
                source=child,
                relation=SUBCONCEPT_RELATION,
                target=parent,
                claim_index=claim.index,
            ))

    return graph


def render_graph(graph: KnowledgeGraph) -> str:
    """Render the taxonomy as the knowledge layer the canon is actually loaded with.

    Edges only: one `"Concept A" --sousConceptDe--> "Concept B"` per line, in claim order,
    identical pairs collapsed. No header, no node table, no prose — the layer *is* the
    hierarchy.
    """
    if not graph.claims:
        return ""

    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    grouped = graph.edges_by_claim()
    for claim in graph.claims:
        for edge in grouped.get(claim.index, []):
            child, parent = graph.node(edge.source), graph.node(edge.target)
            if child is None or parent is None:
                continue
            pair = (child.label, parent.label)
            if pair in seen:
                continue
            seen.add(pair)
            lines.append(f'"{child.label}" --{edge.relation}--> "{parent.label}"')

    return "\n".join(lines)


def graph_stats(text: str) -> dict:
    """Describe the extracted taxonomy — for the setup screen and the report.

    `claims_preserved` is False by design for this form: the rendering is the edge list,
    so the sentences do not travel with it. `source` names the reader that ran, and
    `fallback_reason` is set when the LLM path was asked for and could not run.
    """
    graph = extract_graph(text)
    rendered = render_graph(graph)
    return {
        "source": graph.source,
        "model": graph.model,
        "fallback_reason": ce.last_failure() if graph.source == "rules" else None,
        "subject": graph.subject,
        "aliases": graph.aliases,
        "n_nodes": len(graph.nodes),
        "n_edges": len(graph.edges),
        "n_claims": len(graph.claims),
        "node_kinds": graph.node_kinds(),
        "relations": graph.relations(),
        "rendered_chars": len(rendered),
        "claims_preserved": ks.preserves_claims(text, rendered),
    }


def graph_payload(text: str) -> dict:
    """The graph as plain JSON — what the setup screen draws before the volley is fired."""
    graph = extract_graph(text)
    return {
        "source": graph.source,
        "model": graph.model,
        "subject": graph.subject,
        "aliases": graph.aliases,
        "nodes": [{"id": n.id, "label": n.label, "kind": n.kind} for n in graph.nodes],
        "edges": [
            {"source": e.source, "relation": e.relation,
             "target": e.target, "claimIndex": e.claim_index}
            for e in graph.edges
        ],
    }
