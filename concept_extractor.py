"""
Canon Ball Concept Extractor
Reads a prose knowledge layer into concepts and subsumption links — with an LLM, in two
passes.

Pass 1 names the concepts the text is about and picks the single most general one as the
subject. Pass 2 is handed *only* that concept list (plus the text) and asked which concept
is a sub-concept of which. Nothing else is asked for: the layer the test arm fires carries
one relation, `sousConceptDe`, so the second pass has exactly one job.

Both passes run at temperature 0 against a frontier model through OpenRouter, and the
result is cached per (text, model). The setup screen re-previews on every edit — an
uncached frontier call per keystroke would be slow and expensive.

    EXTRACTION_MODEL / $KS_EXTRACTION_MODEL   the OpenRouter slug both passes run on
    extract(text) -> Extraction | None        None when the LLM path is unavailable

This is NOT deterministic the way the rule-based reader in knowledge_graph.py is. Same
prose and same model will hand back the same graph *within a process* because of the
cache, but a fresh process may read the prose slightly differently. When no key is set,
the host is unreachable, or the model answers with something that is not the JSON it was
asked for, `extract` returns None and knowledge_graph falls back to the rule-based reader
— which is what keeps the test suite and `fire_structure_study.py --dry-run` working with
no key and no network.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field

import requests


# OpenRouter's catalogue moves faster than this file does. Any slug it serves works here;
# check https://openrouter.ai/models and set KS_EXTRACTION_MODEL if this default has been
# retired — an unknown slug is a 400, which lands in the rule-based fallback.
DEFAULT_EXTRACTION_MODEL = "anthropic/claude-sonnet-4.5"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 90

# A knowledge layer is a system prompt, not a corpus. Past this many concepts the taxonomy
# stops being a layer and starts being a dump.
MAX_CONCEPTS = 40
MAX_CONCEPT_CHARS = 80

_CONCEPTS_TOKENS = 1500
_LINKS_TOKENS = 2000

_cache: dict[tuple[str, str], "Extraction | None"] = {}
_last_failure: str | None = None


@dataclass
class Extraction:
    """What the two passes read out of the prose."""
    subject: str
    concepts: list[str] = field(default_factory=list)
    # (child, parent) — the child is a sub-concept of the parent.
    links: list[tuple[str, str]] = field(default_factory=list)
    model: str = ""
    latency_ms: float = 0.0


def extraction_model() -> str:
    try:
        from backend.config import extraction_model as configured
        slug = configured()
    except ImportError:
        slug = os.environ.get("KS_EXTRACTION_MODEL", "").strip()
    return slug or DEFAULT_EXTRACTION_MODEL


def _openrouter_key() -> str:
    try:
        from backend.config import openrouter_key
        return openrouter_key()
    except ImportError:
        pass
    return os.environ.get("OPENROUTER_API_KEY", "")


def available() -> bool:
    """True when the LLM path has a key to run on. Says nothing about reachability."""
    return bool(_openrouter_key())


def last_failure() -> str | None:
    """Why the most recent extraction fell back, or None. Surfaced in the payload."""
    return _last_failure


# ───────────────────────────── the model call ─────────────────────────────

def _chat_json(prompt: str, model: str, max_tokens: int):
    """One extraction turn. Temperature 0, JSON back, no conversation."""
    key = _openrouter_key()
    if not key:
        raise RuntimeError("no OPENROUTER_API_KEY set")

    resp = requests.post(OPENROUTER_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ArthurSrZ/canon_ball",
        "X-Title": "Canon Ball",
    }, timeout=REQUEST_TIMEOUT)

    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")
    return _parse_json(resp.json()["choices"][0]["message"]["content"])


def _parse_json(content: str):
    """Pull the JSON object out of a reply that may be fenced or prefaced."""
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    span = re.search(r"[\{\[].*[\}\]]", text, re.S)
    if not span:
        raise ValueError(f"no JSON in reply: {content[:200]!r}")
    return json.loads(span.group(0))


# ───────────────────────────── pass 1: concepts ─────────────────────────────

CONCEPTS_PROMPT = """You are reading a knowledge layer to build a concept taxonomy.

Return STRICT JSON and nothing else, in this exact shape:
{{"subject": "...", "concepts": ["...", "..."]}}

Rules:
- "subject" is the single most general concept the text is about — the one every other \
concept sits under.
- "concepts" lists every distinct concept the text names, including the subject, at most \
{max_concepts} of them, most important first.
- A concept is a noun phrase, in the text's own wording, trimmed of articles. Never a \
sentence, never a verb phrase, at most {max_chars} characters.
- Do not invent concepts the text does not name. Do not translate.
- No markdown, no commentary, JSON only.

TEXT:
{text}"""


def extract_concepts(text: str, model: str) -> tuple[str, list[str]]:
    data = _chat_json(
        CONCEPTS_PROMPT.format(text=text.strip(), max_concepts=MAX_CONCEPTS,
                               max_chars=MAX_CONCEPT_CHARS),
        model, _CONCEPTS_TOKENS,
    )
    if not isinstance(data, dict):
        raise ValueError("pass 1 did not return an object")

    subject = _clean_concept(str(data.get("subject", "")))
    concepts: list[str] = []
    seen: set[str] = set()
    for raw in [subject, *(data.get("concepts") or [])]:
        label = _clean_concept(str(raw))
        key = label.casefold()
        if label and key not in seen:
            seen.add(key)
            concepts.append(label)

    if not concepts:
        raise ValueError("pass 1 named no concepts")
    return subject or concepts[0], concepts[:MAX_CONCEPTS]


def _clean_concept(label: str) -> str:
    label = re.sub(r"\s+", " ", label).strip().strip('"\'' + " \t,;:.")
    label = re.sub(r"^(?:a|an|the|les|le|la|un|une|des)\s+", "", label, flags=re.IGNORECASE)
    return label[:MAX_CONCEPT_CHARS].strip()


# ───────────────────────────── pass 2: subsumption ─────────────────────────────

LINKS_PROMPT = """Here is a text and the concepts extracted from it.

Return STRICT JSON and nothing else, in this exact shape:
{{"links": [["child", "parent"], ["child", "parent"]]}}

A link ["A", "B"] means **A is a sub-concept of B**: A is a kind of B, a part of B, or an \
instance of B — B is the more general of the two.

Rules:
- Use ONLY the concepts listed below, spelled exactly as listed. Never introduce a new one.
- "{subject}" is the root: it is nobody's child.
- Every other concept must appear as a child at least once, so nothing is left floating.
- Prefer the closest parent, not the root, whenever the text supports a tighter one.
- No cycles. Never link a concept to itself.
- No markdown, no commentary, JSON only.

CONCEPTS:
{concepts}

TEXT:
{text}"""


def extract_links(text: str, subject: str, concepts: list[str], model: str
                  ) -> list[tuple[str, str]]:
    data = _chat_json(
        LINKS_PROMPT.format(
            text=text.strip(), subject=subject,
            concepts="\n".join(f"- {c}" for c in concepts),
        ),
        model, _LINKS_TOKENS,
    )
    raw = data.get("links") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise ValueError("pass 2 did not return a link list")

    pairs: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            child, parent = item.get("child"), item.get("parent")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            child, parent = item
        else:
            continue
        pairs.append((str(child), str(parent)))
    return pairs


def resolve_links(pairs: list[tuple[str, str]], subject: str, concepts: list[str]
                  ) -> list[tuple[str, str]]:
    """Keep the links a taxonomy can actually carry, and hang the leftovers off the root.

    The model is told the rules; this is where they are enforced. Unknown endpoints are
    dropped rather than silently added as concepts — a link naming something that was
    never extracted is the model drifting, not a discovery.
    """
    canonical = {c.casefold(): c for c in concepts}
    parents: dict[str, list[str]] = {}
    links: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def reaches(start: str, goal: str) -> bool:
        stack, visited = [start], set()
        while stack:
            node = stack.pop()
            if node == goal:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(parents.get(node, []))
        return False

    for raw_child, raw_parent in pairs:
        child = canonical.get(_clean_concept(raw_child).casefold())
        parent = canonical.get(_clean_concept(raw_parent).casefold())
        if not child or not parent or child == parent:
            continue
        if child == subject:          # the root is nobody's child
            continue
        if (child, parent) in seen:
            continue
        if reaches(parent, child):    # would close a cycle
            continue
        seen.add((child, parent))
        parents.setdefault(child, []).append(parent)
        links.append((child, parent))

    # Anything the model left floating still belongs to the layer: hang it off the root,
    # the same way the rule-based reader keeps the taxonomy one tree.
    for concept in concepts:
        if concept != subject and concept not in parents:
            links.append((concept, subject))
            parents.setdefault(concept, []).append(subject)

    return links


# ───────────────────────────── the two passes together ─────────────────────────────

def extract(text: str) -> Extraction | None:
    """Read prose into concepts + subsumption links, or None if the LLM path can't run."""
    global _last_failure

    if not text or not text.strip():
        return None

    model = extraction_model()
    key = (text.strip(), model)
    if key in _cache:
        return _cache[key]

    if not available():
        _last_failure = "no OPENROUTER_API_KEY set"
        return None

    started = time.time()
    try:
        subject, concepts = extract_concepts(text, model)
        pairs = extract_links(text, subject, concepts, model)
    except Exception as exc:                      # noqa: BLE001 — any failure falls back
        _last_failure = f"{type(exc).__name__}: {exc}"
        print(f"Concept extraction fell back to the rule-based reader — {_last_failure}",
              flush=True)
        _cache[key] = None
        return None

    extraction = Extraction(
        subject=subject,
        concepts=concepts,
        links=resolve_links(pairs, subject, concepts),
        model=model,
        latency_ms=(time.time() - started) * 1000,
    )
    _last_failure = None
    _cache[key] = extraction
    return extraction


def clear_cache() -> None:
    """Drop the memoised extractions — for tests, and for a deliberate re-read."""
    _cache.clear()
