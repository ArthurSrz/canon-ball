"""Experiment endpoints — fire trials, retrieve results."""

import json
import threading
import uuid
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.schemas import FireRequest
import canon_experiment as ce
import canon_analysis as ca

router = APIRouter()

RESULTS_DIR = Path("results")

# UMAP/Numba workqueue is NOT thread-safe. Serialize all UMAP calls.
_umap_lock = threading.Lock()


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
    experiment_id = str(uuid.uuid4())
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "experiment.json").unlink(missing_ok=True)
    (RESULTS_DIR / "analysis.json").unlink(missing_ok=True)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_experiment_sync, req, experiment_id)


def _build_response(experiment_data: dict, analysis: dict) -> dict:
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



def _run_experiment_sync(req: FireRequest, experiment_id: str):
    run = ce.run_experiment(
        prompt=req.prompt,
        knowledge_layer=req.knowledge_layer,
        n_trials=req.n_trials,
        injection_mode=req.injection_mode,
    )
    ce.save_experiment(run)

    exp_path = RESULTS_DIR / "experiment.json"
    data = json.loads(exp_path.read_text())
    data["experiment_id"] = experiment_id
    exp_path.write_text(json.dumps(data, default=float))

    experiment_data = ce.load_experiment()
    experiment_data["experiment_id"] = experiment_id
    with _umap_lock:
        analysis = ca.full_analysis(experiment_data)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "analysis.json").write_text(
        __import__("json").dumps(analysis, default=float)
    )

    from backend.routers.chain import start_chains_bg
    start_chains_bg(req.prompt, req.knowledge_layer)

    resp = _build_response(experiment_data, analysis)
    resp["experimentId"] = experiment_id
    return resp


@router.get("/results")
def get_results(experiment_id: str | None = None):
    exp_path = RESULTS_DIR / "experiment.json"
    analysis_path = RESULTS_DIR / "analysis.json"
    if not exp_path.exists():
        raise HTTPException(404, "No experiment results found. Fire an experiment first.")
    if not analysis_path.exists():
        raise HTTPException(404, "Analysis not ready yet. Still computing.")

    experiment_data = ce.load_experiment(str(exp_path))
    if experiment_id and experiment_data.get("experiment_id") != experiment_id:
        raise HTTPException(404, "Requested experiment not ready yet.")

    analysis = json.loads(analysis_path.read_text())
    resp = _build_response(experiment_data, analysis)
    resp["experimentId"] = experiment_data.get("experiment_id")
    return resp
