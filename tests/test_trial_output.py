"""Test that a shot is allowed to finish, and that a shot which was cut says so.

The bug these pin down: `max_tokens` was hard-coded to 150, so gemma's answers stopped
mid-sentence and nothing in the response or the UI said why — a cut answer read as a short
one, and its embedding went into the dispersion as if the model had finished talking.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import canon_experiment as ce
from backend.routers.experiment import _build_response


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _openrouter_reply(content, finish_reason):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}


# ───────────────────────────── the budget ─────────────────────────────

def test_the_default_budget_is_no_longer_the_150_that_cut_every_answer():
    assert ce.DEFAULT_MAX_OUTPUT_TOKENS == 512
    assert ce.default_max_output_tokens() == 512


def test_the_budget_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("CANON_MAX_OUTPUT_TOKENS", "2048")
    assert ce.default_max_output_tokens() == 2048
    monkeypatch.setenv("CANON_MAX_OUTPUT_TOKENS", "not a number")
    assert ce.default_max_output_tokens() == ce.DEFAULT_MAX_OUTPUT_TOKENS


def test_the_budget_reaches_the_request_body(monkeypatch):
    sent = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(json)
        return _Resp(_openrouter_reply("done.", "stop"))

    monkeypatch.delenv("HF_API_KEY", raising=False)
    monkeypatch.setattr(ce, "_get_openrouter_key", lambda: "test-key")
    monkeypatch.setattr(ce.requests, "post", fake_post)

    ce.chat_openrouter([{"role": "user", "content": "hi"}], 777)
    assert sent["max_tokens"] == 777


def test_chat_defaults_to_the_configured_budget_when_given_none(monkeypatch):
    seen = {}
    monkeypatch.setattr(ce, "_get_backend", lambda: "cloud")
    monkeypatch.setattr(ce, "chat_openrouter",
                        lambda msgs, budget: seen.setdefault("budget", budget) or ("x", 1.0, "stop"))
    ce.chat([{"role": "user", "content": "hi"}])
    assert seen["budget"] == ce.default_max_output_tokens()


# ───────────────────────────── saying when it was cut ─────────────────────────────

def test_the_backend_s_finish_reason_is_carried_out_of_the_call(monkeypatch):
    monkeypatch.delenv("HF_API_KEY", raising=False)
    monkeypatch.setattr(ce, "_get_openrouter_key", lambda: "test-key")
    monkeypatch.setattr(ce.requests, "post",
                        lambda *a, **k: _Resp(_openrouter_reply("cut off mid-", "length")))
    text, _, reason = ce.chat_openrouter([{"role": "user", "content": "hi"}], 150)
    assert text == "cut off mid-" and reason == "length"


@pytest.mark.parametrize("reason, expected", [("length", True), ("stop", False), ("", False)])
def test_a_trial_is_marked_truncated_only_when_the_budget_was_the_reason(
        monkeypatch, reason, expected):
    monkeypatch.setattr(ce, "chat",
                        lambda msgs, budget=None: ("Alpinism is a practice.", 12.0, reason))
    monkeypatch.setattr(ce, "embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])

    trial = ce.run_single_trial("test", 0, "why?", "", max_tokens=256)
    assert trial.truncated is expected
    assert trial.finish_reason == reason
    assert trial.max_tokens == 256


def test_the_volley_records_the_budget_it_was_fired_with(monkeypatch):
    monkeypatch.setattr(ce, "chat", lambda msgs, budget=None: ("An answer.", 1.0, "stop"))
    monkeypatch.setattr(ce, "embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])
    run = ce.run_experiment("why?", "Alpinism is a sport.", n_trials=1, max_tokens=321)
    assert run.max_tokens == 321
    assert all(t.max_tokens == 321 for t in run.control_trials + run.test_trials)


# ───────────────────────────── what the frontend is handed ─────────────────────────────

def _experiment(truncations):
    """A two-shot-per-arm volley; `truncations` says which shots were cut, in order."""
    trials = []
    for i, cut in enumerate(truncations):
        trials.append({
            "raw_output": "An answer that stops" if cut else "A whole answer.",
            "embeddings": [[0.1, 0.2]],
            "truncated": cut,
            "finish_reason": "length" if cut else "stop",
        })
    half = len(trials) // 2
    return {
        "prompt": "why?", "knowledge_layer": "Alpinism is a sport.", "n_trials": half,
        "max_tokens": 512,
        "control_trials": trials[:half], "test_trials": trials[half:],
    }


def _analysis(n_each):
    pts = [[float(i), float(i)] for i in range(n_each * 2)]
    cents = [[float(i), float(i)] for i in range(n_each * 2)]
    return {
        "comparison": {"control_mean_dispersion": 1.0, "test_mean_dispersion": 0.5,
                       "dispersion_ratio": 0.5, "centroid_shift_cosine": 0.1,
                       "centroid_shift_euclidean": 0.2, "mann_whitney_pvalue": 0.04},
        "projection": {"control_points": pts[:n_each], "test_points": pts[n_each:],
                       "control_centroids": cents[:n_each], "test_centroids": cents[n_each:]},
    }


def test_each_shot_tells_the_frontend_whether_it_was_cut():
    resp = _build_response(_experiment([True, False, False, False]), _analysis(2))
    assert [s["truncated"] for s in resp["control"]] == [True, False]
    assert [s["finishReason"] for s in resp["control"]] == ["length", "stop"]
    assert [s["truncated"] for s in resp["test"]] == [False, False]


def test_the_volley_reports_how_many_shots_were_cut_and_on_what_budget():
    resp = _build_response(_experiment([True, True, False, True]), _analysis(2))
    assert resp["truncatedShots"] == 3
    assert resp["setup"]["maxTokens"] == 512


def test_a_volley_where_nothing_was_cut_says_zero():
    resp = _build_response(_experiment([False] * 4), _analysis(2))
    assert resp["truncatedShots"] == 0
