"""
Canon Ball — FastAPI backend.
Wraps the existing experiment engine, analysis, Borges graph builder,
and Neuronpedia client as REST endpoints.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import experiment, chain

app = FastAPI(title="Canon Ball", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment.router, prefix="/api/experiment", tags=["experiment"])
app.include_router(chain.router, prefix="/api/chain", tags=["chain"])


@app.on_event("startup")
async def warmup():
    """Pre-load fastembed model at startup so first experiment doesn't cold-start."""
    import asyncio
    loop = asyncio.get_event_loop()
    def _warm():
        try:
            from canon_experiment import _get_fastembed
            _get_fastembed()
            print("Embedding model warmed up.", flush=True)
        except Exception as e:
            print(f"Warmup skipped: {e}", flush=True)
    loop.run_in_executor(None, _warm)


@app.get("/health")
def health():
    from backend.config import openrouter_key, neuronpedia_key
    return {
        "status": "ok",
        "openrouter_key_set": bool(openrouter_key()),
        "neuronpedia_key_set": bool(neuronpedia_key()),
    }


# Serve React frontend — must be last
_static = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _static.exists():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(_static / "index.html")
