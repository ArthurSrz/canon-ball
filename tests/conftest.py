"""Keep the suite hermetic.

`extract_graph` reaches for an LLM first and falls back to the rule-based reader. A test
run must not depend on whether a key happens to be in the developer's environment, so the
LLM path is held off for every test by default. A test that wants it stubs the model
itself — see tests/test_concept_extractor.py.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import concept_extractor as ce


@pytest.fixture(autouse=True)
def no_llm_unless_stubbed(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(ce, "_openrouter_key", lambda: "")
    ce.clear_cache()
    yield
    ce.clear_cache()
