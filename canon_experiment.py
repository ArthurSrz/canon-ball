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


def _get_backend():
    """Detect if ollama is available locally, otherwise use cloud."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass
    return "cloud"


def _get_openrouter_key():
    try:
        import streamlit as st
        return st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "")


def _get_fastembed():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding
        _fastembed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _fastembed_model


def chat_ollama(prompt: str, system: str = "") -> tuple[str, float]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

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


def chat_openrouter(prompt: str, system: str = "") -> tuple[str, float]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    key = _get_openrouter_key()
    t0 = time.time()
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json={
        "model": "qwen/qwen-2.5-7b-instruct",
        "messages": messages,
        "temperature": 0.8,
    }, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    latency = (time.time() - t0) * 1000
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
    return resp.json()["choices"][0]["message"]["content"], latency


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


def chat(prompt: str, system: str = "") -> tuple[str, float]:
    if _get_backend() == "ollama":
        return chat_ollama(prompt, system)
    return chat_openrouter(prompt, system)


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
    control_trials: list[Trial] = field(default_factory=list)
    test_trials: list[Trial] = field(default_factory=list)
    timestamp: str = ""


def tokenize_output(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?;:])\s+', text.strip())
    return [c for c in chunks if len(c) > 5]


def run_single_trial(trial_type: str, index: int, prompt: str, knowledge_layer: str) -> Trial:
    system = knowledge_layer if trial_type == "test" else ""
    raw_output, latency = chat(prompt, system=system)
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
                   progress_callback=None) -> ExperimentRun:
    run = ExperimentRun(
        prompt=prompt,
        knowledge_layer=knowledge_layer,
        n_trials=n_trials,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
    )

    total = n_trials * 2
    for i in range(n_trials):
        trial = run_single_trial("control", i, prompt, knowledge_layer)
        run.control_trials.append(trial)
        if progress_callback:
            progress_callback((i + 1) / total, f"Control trial {i+1}/{n_trials}")

    for i in range(n_trials):
        trial = run_single_trial("test", i, prompt, knowledge_layer)
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
