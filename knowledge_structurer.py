"""
Canon Ball Knowledge Structurer
Turns a free-prose knowledge layer into a structured one without changing the facts.

The structurer re-arranges, it does not rewrite: every claim is carried through
verbatim, so a volley fired at `prose` and a volley fired at `schema` differ only
in form. That is what makes the dispersion delta readable as a *structure* effect
rather than a content effect.

Four forms, in increasing order of structure:
    prose       the raw text, untouched (the baseline)
    bullets     one claim per line
    typed_facts subject | relation | claim triples
    schema      claims grouped under typed relation keys
"""

import re
from dataclasses import dataclass, field


STRUCTURE_FORMS = {
    "prose": "Prose (raw)",
    "bullets": "Bullet claims",
    "typed_facts": "Typed facts",
    "schema": "Schema block",
}

# Order matters only for ties — the cue that appears EARLIEST in a claim wins,
# because the claim's head predicate is normally its first one.
RELATION_CUES = [
    ("definition", r"\b(?:is|are|was|were)\s+(?:a|an|the|any|one of|part of)\b"
                   r"|\brefers? to\b|\bmeans\b|\bis defined as\b|\bdesignates\b"),
    ("composition", r"\b(?:includ\w+|comprise\w*|consist\w+|contain\w+|encompass\w+"
                    r"|made up of|such as)\b"),
    ("origin", r"\b(?:emerged|originated|began|arose|was founded|founded|dates? back"
               r"|first appeared|first ascent|earliest|pioneer\w*|starting point"
               r"|invented|developed)\b"),
    ("governance", r"\b(?:governed|regulated|overseen|administered|certified"
                   r"|accredited|standardi[sz]ed)\b"),
    ("purpose", r"\b(?:used (?:for|to)|serves? to|aims? to|intended (?:for|to)|in order to)\b"),
    ("requirement", r"\b(?:requires?|needs?|demands?|depends? on|involves?|must)\b"),
    ("risk", r"\b(?:risk\w*|danger\w*|hazard\w*|fatal\w*|injur\w*|avalanche\w*|accident\w*)\b"),
    ("measure", r"\b\d[\d.,]*\s*(?:%|percent|m|km|metres|meters|feet|ft|years?)\b"),
    ("time", r"\b(?:since|during|until|in the \d{1,2}(?:st|nd|rd|th) century|in \d{4}"
             r"|today|nowadays)\b"),
    ("location", r"\b(?:in|on|across|throughout|near)\s+the\s+[A-Z]\w+|\bin\s+[A-Z]\w+"),
]

DEFAULT_RELATION = "property"

# A claim shorter than this is a fragment, not a fact.
MIN_CLAIM_CHARS = 15

_SUBJECT_HEAD = re.compile(
    r"^(.*?)\s+(?:is|are|was|were|refers|means|includes|comprises|consists|emerged|covers)\b",
    re.IGNORECASE,
)


@dataclass
class Claim:
    """One atomic fact, kept verbatim, plus the relation the cues assigned it."""
    text: str
    relation: str
    index: int


@dataclass
class StructuredKnowledge:
    subject: str
    aliases: list[str] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)

    def by_relation(self) -> dict[str, list[Claim]]:
        """Claims grouped under their relation, in first-appearance order."""
        grouped: dict[str, list[Claim]] = {}
        for claim in self.claims:
            grouped.setdefault(claim.relation, []).append(claim)
        return grouped


def split_claims(text: str) -> list[str]:
    """Cut prose into atomic claims: sentences, then semicolon-joined independent parts."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    claims = []
    for sentence in sentences:
        for part in sentence.split(";"):
            part = part.strip()
            if len(part) >= MIN_CLAIM_CHARS:
                claims.append(part)
    return claims


def classify_claim(claim: str) -> str:
    """Assign a relation by the cue that appears earliest in the claim."""
    best_relation = DEFAULT_RELATION
    best_position = len(claim) + 1
    for relation, pattern in RELATION_CUES:
        match = re.search(pattern, claim, re.IGNORECASE)
        if match and match.start() < best_position:
            best_relation = relation
            best_position = match.start()
    return best_relation


def extract_subject(claims: list[str]) -> tuple[str, list[str]]:
    """Pull the knowledge layer's head subject (and any parenthesised aliases) from claim 1."""
    if not claims:
        return "", []

    head = _SUBJECT_HEAD.match(claims[0])
    raw = head.group(1).strip() if head else " ".join(claims[0].split()[:4])

    aliases = [a.strip() for a in re.findall(r"\(([^)]+)\)", raw) if a.strip()]
    subject = re.sub(r"\s*\([^)]*\)", "", raw).strip(" ,.:—-")
    subject = re.sub(r"^(?:The|A|An)\s+", "", subject, flags=re.IGNORECASE)

    return subject, aliases


def analyze_knowledge(text: str) -> StructuredKnowledge:
    """Read prose into a subject + typed claims, without altering a single claim's wording."""
    raw_claims = split_claims(text)
    subject, aliases = extract_subject(raw_claims)
    claims = [Claim(text=c, relation=classify_claim(c), index=i)
              for i, c in enumerate(raw_claims)]
    return StructuredKnowledge(subject=subject, aliases=aliases, claims=claims)


def _render_bullets(knowledge: StructuredKnowledge) -> str:
    return "\n".join(f"- {c.text}" for c in knowledge.claims)


def _render_typed_facts(knowledge: StructuredKnowledge) -> str:
    subject = knowledge.subject or "subject"
    lines = [f"{subject} | {c.relation} | {c.text}" for c in knowledge.claims]
    header = "subject | relation | claim"
    return "\n".join([header, "-" * len(header), *lines])


def _render_schema(knowledge: StructuredKnowledge) -> str:
    lines = [f"entity: {knowledge.subject or 'subject'}"]
    if knowledge.aliases:
        lines.append(f"aliases: {', '.join(knowledge.aliases)}")
    for relation, claims in knowledge.by_relation().items():
        lines.append(f"{relation}:")
        lines.extend(f"  - {c.text}" for c in claims)
    return "\n".join(lines)


_RENDERERS = {
    "bullets": _render_bullets,
    "typed_facts": _render_typed_facts,
    "schema": _render_schema,
}


def structure_knowledge(text: str, form: str = "prose") -> str:
    """Render a prose knowledge layer in one of STRUCTURE_FORMS. Facts are preserved verbatim."""
    if not text or not text.strip():
        return ""
    if form not in STRUCTURE_FORMS:
        raise ValueError(f"Unknown structure form '{form}'. Known: {list(STRUCTURE_FORMS)}")
    if form == "prose":
        return text.strip()
    return _RENDERERS[form](analyze_knowledge(text))


def preserves_claims(text: str, rendered: str) -> bool:
    """True when every claim of the prose survives verbatim in the rendered form."""
    return all(claim in rendered for claim in split_claims(text))


def structure_stats(text: str, form: str = "prose") -> dict:
    """Describe what the structurer did — for the report and the setup screen."""
    knowledge = analyze_knowledge(text)
    rendered = structure_knowledge(text, form)
    relations = {rel: len(claims) for rel, claims in knowledge.by_relation().items()}
    return {
        "form": form,
        "form_label": STRUCTURE_FORMS.get(form, form),
        "subject": knowledge.subject,
        "aliases": knowledge.aliases,
        "n_claims": len(knowledge.claims),
        "relations": relations,
        "raw_chars": len(text.strip()),
        "rendered_chars": len(rendered),
        "claims_preserved": preserves_claims(text, rendered),
    }
