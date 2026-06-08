# Coding Conventions

**Analysis Date:** 2026-06-08

## Naming Patterns

**Files:**
- Python modules: `snake_case` (e.g., `canon_experiment.py`, `neuronpedia_client.py`, `borges_graph.py`)
- React components: `PascalCase.jsx` (e.g., `App.jsx`, `MapScreen.jsx`, `SemanticMap.jsx`)
- Utility files: `snake_case.js` (e.g., `mockData.js`, `api.js`, `useExperiment.js`)
- Hooks: `useXxx.js` (e.g., `useExperiment.js`)

**Functions (Python):**
- Public functions: `snake_case` (e.g., `run_experiment()`, `compile_attribution()`, `full_analysis()`)
- Private functions: `_snake_case` (leading underscore for module-private, e.g., `_get_backend()`, `_run_experiment_sync()`)
- Dataclass instances and temporary variables: `lowercase_with_underscores`

**Functions (JavaScript):**
- Regular functions: `camelCase` (e.g., `fireExperiment()`, `getResults()`)
- React components: `PascalCase` (e.g., `MapScreen`, `SemanticMap`)
- Hooks: `useCamelCase` (e.g., `useExperiment`, `useTweaks`)
- Private/internal helpers: `_camelCase` (e.g., `_pollUntilDone()`, `_run()`)

**Variables:**
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `OLLAMA_BASE`, `WINDOW_SIZE`, `MAX_NEW_POSITIONS`)
- State variables: `camelCase` in JS (e.g., `isOpen`, `currentStep`), `snake_case` in Python (e.g., `_chain_state`)
- Component props: `camelCase` (e.g., `knowledgeLayer`, `nTrials`, `injectionMode`)

**Types (Python):**
- Dataclasses: `PascalCase` (e.g., `Trial`, `ExperimentRun`, `Feature`, `NLAResult`, `Step`, `CompiledGraph`)
- Type hints use full paths: `list[dict]`, `dict | None` (Python 3.10+ union syntax)

**Types (JavaScript):**
- No TypeScript; JSDoc optional but not enforced
- Implicit object shapes used directly

## Code Style

**Formatting:**
- No linter or formatter configured (eslint, prettier, black, ruff not present)
- Python: follows implicit PEP 8-ish style with 4-space indentation
- JavaScript/JSX: 2-space indentation in components and utilities
- CSS: organized with section comments using `/* ─── Label ───── */` delimiters

**Linting:**
- None configured in the project

**Line Length:**
- No strict line length limit enforced
- Python code is typically ~100 characters per line
- JavaScript is more variable

**Indentation:**
- Python: 4 spaces
- JavaScript/JSX: 2 spaces
- CSS: 2 spaces

## Import Organization

**Python Order:**
1. Standard library imports (`json`, `os`, `time`, `requests`, `re`, `pathlib`)
2. Third-party imports (`numpy`, `fastapi`, `pydantic`, `scipy`, `sklearn`, `umap`, `fastembed`)
3. Local imports (`backend.routers`, `backend.config`, `canon_experiment`)
4. Relative imports (within same module)

Example from `backend/main.py`:
```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import experiment, chain
```

**JavaScript Order:**
1. React/framework imports (`react`, `react-dom`)
2. Internal component/hook imports (relative paths)
3. Utility/API imports

Example from `App.jsx`:
```javascript
import React, { useState, useEffect } from 'react'
import { useExperiment } from './hooks/useExperiment'
import MOCK_DATA from './mockData'
```

**Path Aliases:**
- Not used; relative imports only (`./`, `../`)
- Backend uses absolute imports from project root (`from backend.routers import ...`)

## Error Handling

**Python Patterns:**
- Explicit exception handling with `try/except` and informative error messages
- HTTP errors wrapped in `HTTPException` with status code and message (see `backend/routers/experiment.py:135`)
- Runtime errors raised with context (e.g., `RuntimeError("No OPENROUTER_API_KEY or HF_API_KEY set.")`)
- Network errors: `resp.raise_for_status()` for validation, status code checks for graceful degradation
- Silent fallbacks for optional operations (e.g., warmup skipped on startup if embedding model unavailable)

Example from `canon_experiment.py:89-95`:
```python
def chat_openrouter(messages: list[dict]) -> tuple[str, float]:
    key = _get_openrouter_key()
    if not key:
        raise RuntimeError("No OPENROUTER_API_KEY or HF_API_KEY set.")
    # ... request ...
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
```

**JavaScript Patterns:**
- `try/catch` in async functions; errors logged or state-updated
- HTTP errors: check `res.ok`, throw `Error(await res.text())` for debugging
- Graceful error recovery: polling fallback if initial fetch times out
- State-based error display (e.g., `error` state in `useExperiment`)

Example from `hooks/useExperiment.js:26-46`:
```javascript
try {
  const result = await Promise.race([fetchPromise, timeout])
  setResult(result)
  setStatus('done')
} catch (err) {
  setError(err.message)
  setStatus('error')
  throw err
}
```

## Logging

**Framework:** `print()` (Python), `console.log()` (JavaScript)

**Patterns (Python):**
- Server startup: `print(..., flush=True)` to force immediate output (see `backend/main.py:38`)
- Error context: `print(f"Chain pre-compute failed: {e}", flush=True)` (see `backend/routers/chain.py:58`)
- Spare use of logging; print statements are debug-oriented

**Patterns (JavaScript):**
- Console logging for development; not visible in production UI
- Status updates via React state instead of logs (e.g., `setStatus('computing')`)

## Comments

**When to Comment:**
- Explain complex algorithms or mathematical operations (e.g., UMAP normalization, statistical tests)
- Mark non-obvious workarounds or hacks (e.g., backend auto-detection fallback, warmup skipping)
- Document module purpose in docstrings
- Explain why a constraint exists (e.g., "UMAP/Numba workqueue is NOT thread-safe")

Example from `backend/routers/experiment.py:18-19`:
```python
# UMAP/Numba workqueue is NOT thread-safe. Serialize all UMAP calls.
_umap_lock = threading.Lock()
```

**JSDoc/TSDoc:**
- Not enforced; Python modules use docstrings for public functions
- Python docstrings are present but minimal (see `canon_experiment.py:1-8`)
- JavaScript functions lack docstrings; logic is self-documenting

Example Python docstring from `borges_graph.py:1-26`:
```python
"""
Borges Graph — Compiled Attribution Graph Builder

Standalone library wrapping the Neuronpedia Circuit Tracer API. No Streamlit dependency.

Usage:
    from borges_graph import compile_attribution
    ...
"""
```

## Function Design

**Size:**
- Small functions for distinct responsibilities (e.g., `_normalize_projection()`, `embed_fastembed()`)
- Longer functions acceptable if they're algorithms or orchestrators (e.g., `_build_focal_scene()` at 102 lines)
- Utility functions are typically 10–40 lines

**Parameters:**
- Python: ordered positional args, followed by optional keyword args with defaults
- JavaScript: single object parameter for component props, destructured in signature
- Avoid boolean parameters for behavior divergence; use enum-style strings (e.g., `trial_type: str`, `injection_mode: str`)

Example from `canon_experiment.py:228-229`:
```python
def run_single_trial(trial_type: str, index: int, prompt: str, knowledge_layer: str,
                     injection_mode: str = "system_user") -> Trial:
```

**Return Values:**
- Python: typed return annotations (e.g., `-> tuple[str, float]`, `-> dict`, `-> CompiledGraph`)
- Single return value or tuple of closely related values
- Complex returns packaged in dataclasses (e.g., `Trial`, `NLAResult`, `CompiledGraph`)
- JavaScript: implicit types; return plain objects or React elements

## Module Design

**Exports (Python):**
- No explicit `__all__`; public functions are assumed to be those not prefixed with `_`
- Dataclasses (Trial, ExperimentRun, etc.) exported implicitly for type hints

**Exports (JavaScript):**
- Default exports for React components (e.g., `export default function MapScreen(...)`)
- Named exports for utilities and hooks (e.g., `export function useTweaks(...)`, `export async function fireExperiment(...)`)
- Re-exports rare; most utilities imported directly from their source

**Barrel Files:**
- Not used; direct imports from source files
- Example: `import { useTweaks } from '../components/TweaksPanel'` (not from index)

## Code Organization Patterns

**Python Modules:**
- Global constants at top: `OLLAMA_BASE`, `INJECTION_MODES`, `MAX_NEW_POSITIONS`
- Module-level cache/state: `_fastembed_model`, `_backend_cache`, `_chain_state`
- Helper functions prefixed with `_` before public functions
- Dataclasses near top after imports
- Main orchestration functions (`run_experiment`, `compile_attribution`, `full_analysis`) near bottom

**React Components:**
- Props destructured in signature
- Local state (`useState`) declared first
- Event handlers and render logic inline
- Inline styles via objects for dynamic theming
- CSS classes for static design system tokens

Example from `MapScreen.jsx:4-7`:
```javascript
export default function MapScreen({ data, playful, go, runKey, replay, motion }) {
  const [showC, setShowC] = useState(true)
  const [showT, setShowT] = useState(true)
  const [picked, setPicked] = useState(null)
```

## Design System & Styling

**CSS Architecture:**
- Single global stylesheet (`frontend/src/styles.css`) with CSS variables
- RawBlock brutalist design system: white ground, black borders, no shadows
- Design signal colors: `--control` (black), `--test` (red), `--gold` (orange knowledge), `--link` (blue hyperlinks)
- Typography: `--display` (Archivo Black), `--ui` (Work Sans), `--mono` (Space Mono)

**Inline Styles (React):**
- Used extensively for component-specific layout and animations
- Props like `style={{ display: "grid", placeItems: "center" }}`
- Dynamic values via JavaScript (e.g., `transform={`rotate(${angle} 40 40)`}`)

---

*Convention analysis: 2026-06-08*
