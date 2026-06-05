"""
Canon Ball Experiment Engine
Measures the semantic precision of LLM outputs with and without a knowledge layer.

Supports two backends:
- Local: ollama (qwen2.5:3b + bge-m3)
- Cloud: OpenRouter (qwen2.5:3b) + fastembed (BAAI/bge-small-en-v1.5)
"""

import json
import os
import re
import time
import requests
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict


OLLAMA_BASE = "http://localhost:11434"

_fastembed_model = None
_backend_cache: str | None = None


INJECTION_MODES = {
    "system_user": "System → User",
    "interleave": "Interleaved",
    "template": "Template injection",
    "cot_priming": "CoT priming",
}


def _get_backend():
    """Detect if ollama is available locally, otherwise use cloud (OpenRouter + fastembed).

    Result is cached for the process — without the cache every chat/embed call probes
    localhost:11434, which on remote (Streamlit Cloud) blocks ~2s per call.
    Set CANON_BACKEND=cloud (or =ollama) to force a backend explicitly.
    """
    global _backend_cache
    if _backend_cache is not None:
        return _backend_cache
    forced = os.environ.get("CANON_BACKEND", "cloud").strip().lower()
    if forced in ("ollama", "cloud"):
        _backend_cache = forced
        return _backend_cache
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1.5)
        if r.status_code == 200:
            _backend_cache = "ollama"
            return _backend_cache
    except Exception:
        pass
    _backend_cache = "cloud"
    return _backend_cache


def _get_openrouter_key():
    try:
        from backend.config import openrouter_key
        return openrouter_key()
    except ImportError:
        pass
    return os.environ.get("OPENROUTER_API_KEY", "")


def _get_fastembed():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding
        _fastembed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _fastembed_model


def chat_ollama(messages: list[dict]) -> tuple[str, float]:
    t0 = time.time()
    resp = requests.post(f"{OLLAMA_BASE}/api/chat", json={
        "model": "qwen2.5:3b",
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.8, "seed": -1}
    })
    latency = (time.time() - t0) * 1000
    resp.raise_for_status()
    return resp.json()["message"]["content"], latency


def chat_openrouter(messages: list[dict]) -> tuple[str, float]:
    hf_key = os.environ.get("HF_API_KEY", "")
    if hf_key:
        return _chat_hf(messages, hf_key)
    key = _get_openrouter_key()
    if not key:
        raise RuntimeError("No OPENROUTER_API_KEY or HF_API_KEY set.")
    t0 = time.time()
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json={
        "model": "google/gemma-3-4b-it",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 150,
    }, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ArthurSrZ/canon_ball",
        "X-Title": "Canon Ball",
    }, timeout=60)
    latency = (time.time() - t0) * 1000
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
    return resp.json()["choices"][0]["message"]["content"], latency


def _chat_hf(messages: list[dict], key: str) -> tuple[str, float]:
    # gemma-2-2b-it on featherless-ai doesn't support system role — fold into user
    normalized = []
    for m in messages:
        role = "user" if m["role"] == "system" else m["role"]
        if normalized and normalized[-1]["role"] == role:
            normalized[-1]["content"] += "\n" + m["content"]
        else:
            normalized.append({"role": role, "content": m["content"]})
    t0 = time.time()
    resp = requests.post(
        "https://router.huggingface.co/featherless-ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "google/gemma-2-2b-it",
            "messages": normalized,
            "max_tokens": 150,
            "temperature": 0.8,
        },
        timeout=60,
    )
    latency = (time.time() - t0) * 1000
    if resp.status_code != 200:
        raise RuntimeError(f"HF {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"].strip(), latency


def embed_ollama(texts: list[str]) -> list[list[float]]:
    resp = requests.post(f"{OLLAMA_BASE}/api/embed", json={
        "model": "bge-m3",
        "input": texts
    })
    resp.raise_for_status()
    return resp.json()["embeddings"]


def embed_fastembed(texts: list[str]) -> list[list[float]]:
    model = _get_fastembed()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def chat(messages: list[dict]) -> tuple[str, float]:
    if _get_backend() == "ollama":
        return chat_ollama(messages)
    return chat_openrouter(messages)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if _get_backend() == "ollama":
        return embed_ollama(texts)
    return embed_fastembed(texts)


@dataclass
class Trial:
    trial_type: str
    trial_index: int
    prompt: str
    knowledge_layer: str
    raw_output: str
    output_tokens: list[str]
    embeddings: list[list[float]]
    latency_ms: float


@dataclass
class ExperimentRun:
    prompt: str
    knowledge_layer: str
    n_trials: int
    injection_mode: str = "system_user"
    control_trials: list[Trial] = field(default_factory=list)
    test_trials: list[Trial] = field(default_factory=list)
    timestamp: str = ""


def tokenize_output(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?;:])\s+', text.strip())
    return [c for c in chunks if len(c) > 5]


def assemble_messages(prompt: str, knowledge_layer: str, mode: str) -> list[dict]:
    if mode == "system_user":
        msgs = []
        if knowledge_layer:
            msgs.append({"role": "system", "content": knowledge_layer})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    if mode == "interleave":
        k_parts = [s.strip() for s in re.split(r'\n{2,}', knowledge_layer.strip()) if s.strip()]
        p_parts = re.split(r'(?<=[.!?])\s+', prompt.strip())
        merged = []
        for i in range(max(len(p_parts), len(k_parts))):
            if i < len(p_parts):
                merged.append(p_parts[i])
            if i < len(k_parts):
                merged.append(k_parts[i])
        return [{"role": "user", "content": "\n\n".join(merged)}]

    if mode == "template":
        return [{"role": "user", "content": f"{prompt}\n\n---\nContext:\n{knowledge_layer}"}]

    if mode == "cot_priming":
        return [
            {"role": "user", "content": "What do you know about this topic?"},
            {"role": "assistant", "content": knowledge_layer},
            {"role": "user", "content": prompt},
        ]

    return [{"role": "user", "content": prompt}]


def run_single_trial(trial_type: str, index: int, prompt: str, knowledge_layer: str,
                     injection_mode: str = "system_user") -> Trial:
    if trial_type == "test":
        messages = assemble_messages(prompt, knowledge_layer, injection_mode)
    else:
        messages = [{"role": "user", "content": prompt}]
    raw_output, latency = chat(messages)
    chunks = tokenize_output(raw_output)

    if not chunks:
        chunks = [raw_output[:200]] if raw_output else ["(empty)"]

    embeddings = embed_texts(chunks)

    return Trial(
        trial_type=trial_type,
        trial_index=index,
        prompt=prompt,
        knowledge_layer=knowledge_layer if trial_type == "test" else "",
        raw_output=raw_output,
        output_tokens=chunks,
        embeddings=embeddings,
        latency_ms=latency
    )


def run_experiment(prompt: str, knowledge_layer: str, n_trials: int = 12,
                   injection_mode: str = "system_user",
                   progress_callback=None) -> ExperimentRun:
    run = ExperimentRun(
        prompt=prompt,
        knowledge_layer=knowledge_layer,
        n_trials=n_trials,
        injection_mode=injection_mode,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
    )

    total = n_trials * 2
    for i in range(n_trials):
        trial = run_single_trial("control", i, prompt, knowledge_layer, injection_mode)
        run.control_trials.append(trial)
        if progress_callback:
            progress_callback((i + 1) / total, f"Control trial {i+1}/{n_trials}")

    for i in range(n_trials):
        trial = run_single_trial("test", i, prompt, knowledge_layer, injection_mode)
        run.test_trials.append(trial)
        if progress_callback:
            progress_callback((n_trials + i + 1) / total, f"Test trial {i+1}/{n_trials}")

    return run


def save_experiment(run: ExperimentRun, path: str = "results/experiment.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    data = {
        "prompt": run.prompt,
        "knowledge_layer": run.knowledge_layer,
        "n_trials": run.n_trials,
        "injection_mode": run.injection_mode,
        "timestamp": run.timestamp,
        "control_trials": [asdict(t) for t in run.control_trials],
        "test_trials": [asdict(t) for t in run.test_trials],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_experiment(path: str = "results/experiment.json") -> dict:
    with open(path) as f:
        return json.load(f)
