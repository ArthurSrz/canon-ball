"""
Unified config — replaces st.secrets lookups throughout the codebase.
Reads from environment variables or a .env file.
"""

import os
from pathlib import Path


def _load_dotenv():
    """Load .env file if present (no dependency on python-dotenv)."""
    for candidate in [Path(".env"), Path(__file__).resolve().parent.parent / ".env"]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = value
            break


_load_dotenv()


def openrouter_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def neuronpedia_key() -> str:
    return os.environ.get("NEURONPEDIA_API_KEY", "")


def hf_key() -> str:
    return os.environ.get("HF_API_KEY", "")
