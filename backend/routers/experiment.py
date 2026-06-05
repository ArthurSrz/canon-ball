"""Experiment endpoints — fire trials, retrieve results."""

import json
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.schemas import FireRequest
import canon_experiment as ce
import canon_analysis as ca

router = APIRouter()

RESULTS_DIR = Path("results")


def _normalize_projection(projection: dict, trials_ctrl: list[dict], trials_test: list[dict]) -> dict:
    """Reshape canon_analysis projection into the frontend's per-trial format.

    Frontend expects:
      control/test: [{index, centroid: {x,y}, chunks: [{x,y}], output}, ...]
    Normalized to [0, 100] field.
    """
    all_pts = projection["control_points"] + projection["test_points"]
    all_cents = projection["control_centroids"] + projection["test_centroids"]
    everything = np.array(all_pts + all_cents)

    lo = everything.min(axis=0)
    hi = everything.max(axis=0)
    span = hi - lo
    span[span == 0] = 1

    def norm(pt):
        return {"x": float((pt[0] - lo[0]) / span[0] * 90 + 5),
                "y": float((pt[1] - lo[1]) / span[1] * 90 + 5)}

    def build_group(trials, points, centroids):
        result = []
        idx = 0
        for i, t in enumerate(trials):
            n_chunks = len(t["embeddings"])
            chunks = [norm(points[idx + j]) for j in range(n_chunks)]
            idx += n_chunks
            result.append({
                "index": i,
                "centroid": norm(centroids[i]),
                "chunks": chunks,
                "output": t["raw_output"],
            })
        return result

    ctrl = build_group(trials_ctrl, projection["control_points"], projection["control_centroids"])
    test = build_group(trials_test, projection["test_points"], projection["test_centroids"])
    return {"control": ctrl, "test": test}


@router.post("/fire")
async def fire_experiment(req: FireRequest):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_experiment_sync, req)


def _compile_chains_bg(prompt: str, knowledge_layer: str, max_tokens: int = 6):
    """Pre-compute Borges chains in background after experiment fires."""
    import threading
    import borges_graph as bg

    def _run():
        try:
            RESULTS_DIR.mkdir(exist_ok=True)
            # Control chain (no KL)
            ctrl = bg.compile_attribution(prompt, system_prompt="", max_tokens=max_tokens)
            (RESULTS_DIR / "chain_control.json").write_text(
                __import__("json").dumps(ctrl.to_dict(), indent=2)
            )
            # Test chain (with KL)
            test = bg.compile_attribution(prompt, system_prompt=knowledge_layer, max_tokens=max_tokens)
            (RESULTS_DIR / "chain_test.json").write_text(
                __import__("json").dumps(test.to_dict(), indent=2)
            )
            print("Borges chains saved.", flush=True)
        except Exception as e:
            print(f"Chain pre-compute failed: {e}", flush=True)

    threading.Thread(target=_run, daemon=True).start()


def _run_experiment_sync(req: FireRequest):
    run = ce.run_experiment(
        prompt=req.prompt,
        knowledge_layer=req.knowledge_layer,
        n_trials=req.n_trials,
        injection_mode=req.injection_mode,
    )
    ce.save_experiment(run)

    # Kick off chain computation in background (doesn't block response)
    _compile_chains_bg(req.prompt, req.knowledge_layer)

    experiment_data = ce.load_experiment()
    analysis = ca.full_analysis(experiment_data)

    comparison = analysis["comparison"]
    projection = analysis["projection"]
    groups = _normalize_projection(
        projection,
        experiment_data["control_trials"],
        experiment_data["test_trials"],
    )

    tightening = (1 - comparison["dispersion_ratio"]) * 100 if comparison["dispersion_ratio"] else 0

    return {
        "setup": {
            "prompt": req.prompt,
            "knowledgeLayer": req.knowledge_layer,
            "nTrials": req.n_trials,
            "model": "gemma-3-4b-it",
            "embedder": "bge-small-en-v1.5",
        },
        "control": groups["control"],
        "test": groups["test"],
        "N": req.n_trials,
        "comparison": {
            "controlMeanDispersion": comparison["control_mean_dispersion"],
            "testMeanDispersion": comparison["test_mean_dispersion"],
            "dispersionRatio": comparison["dispersion_ratio"],
            "tighteningPct": round(tightening, 1),
            "centroidShiftCosine": comparison["centroid_shift_cosine"],
            "centroidShiftEuclidean": comparison["centroid_shift_euclidean"],
            "mannWhitneyP": comparison["mann_whitney_pvalue"],
        },
    }


@router.get("/results")
def get_results():
    exp_path = RESULTS_DIR / "experiment.json"
    if not exp_path.exists():
        raise HTTPException(404, "No experiment results found. Fire an experiment first.")

    experiment_data = ce.load_experiment(str(exp_path))
    analysis = ca.full_analysis(experiment_data)

    comparison = analysis["comparison"]
    projection = analysis["projection"]
    groups = _normalize_projection(
        projection,
        experiment_data["control_trials"],
        experiment_data["test_trials"],
    )

    tightening = (1 - comparison["dispersion_ratio"]) * 100 if comparison["dispersion_ratio"] else 0

    return {
        "setup": {
            "prompt": experiment_data["prompt"],
            "knowledgeLayer": experiment_data["knowledge_layer"],
            "nTrials": experiment_data["n_trials"],
            "model": "gemma-3-4b-it",
            "embedder": "bge-small-en-v1.5",
        },
        "control": groups["control"],
        "test": groups["test"],
        "N": experiment_data["n_trials"],
        "comparison": {
            "controlMeanDispersion": comparison["control_mean_dispersion"],
            "testMeanDispersion": comparison["test_mean_dispersion"],
            "dispersionRatio": comparison["dispersion_ratio"],
            "tighteningPct": round(tightening, 1),
            "centroidShiftCosine": comparison["centroid_shift_cosine"],
            "centroidShiftEuclidean": comparison["centroid_shift_euclidean"],
            "mannWhitneyP": comparison["mann_whitney_pvalue"],
        },
    }
