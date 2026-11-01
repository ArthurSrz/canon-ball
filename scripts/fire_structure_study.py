#!/usr/bin/env python3
"""
Fire the structure study: what does STRUCTURING a knowledge layer add?

Every volley draws on the same prose. The control arm and the test arm differ only in
the form that prose is rendered in, so the dispersion delta reads as a structure effect
rather than a content effect.

    python3 scripts/fire_structure_study.py                    # the full study
    python3 scripts/fire_structure_study.py --dry-run          # no API key, no network
    python3 scripts/fire_structure_study.py --n 8 --mode system_user
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import canon_analysis as ca
import canon_experiment as ce
import knowledge_structurer as ks


PROMPT = "Write a short reflection on why people climb mountains."

KNOWLEDGE = (
    "Mountaineering (alpinism) is the set of sporting and leisure activities that involve "
    "ascending mountains, including rock climbing, ice climbing, ski touring and hiking "
    "across glaciated terrain. It emerged in the Alps in the 18th century; the 1786 ascent "
    "of Mont Blanc by Jacques Balmat and Michel-Gabriel Paccard is its conventional starting "
    "point. It is governed today by national alpine federations, federated under the UIAA, "
    "founded in 1932. The discipline distinguishes alpine style, where climbers carry their "
    "own gear in a single push, from expedition style, which relies on fixed camps and ropes. "
    "Above roughly 8000 m climbers enter the death zone, where the body no longer acclimatises. "
    "Its principal hazards are avalanches, crevasse falls, rockfall and altitude sickness. "
    "Required skills include rope work, belaying, crampon and ice-axe technique, and crevasse "
    "rescue. Fourteen peaks exceed 8000 m, all of them in the Himalaya and the Karakoram."
)

# (label, control arm form, test arm form)
# The test arm has one form — the knowledge graph. The first volley is the historical
# Canon Ball measure (what knowledge adds); the last is the structure measure (what the
# graph adds on top of the very same facts in prose).
VOLLEYS = [
    ("Prose vs rien", "none", "prose"),
    ("Graphe vs rien", "none", ks.TEST_ARM_FORM),
    ("Graphe vs prose", "prose", ks.TEST_ARM_FORM),
]


def _install_dry_run_stubs():
    """Replace the model and the embedder with deterministic stand-ins.

    Lets the whole pipeline — structurer, volley, UMAP, report — be exercised with no API
    key and no network. The numbers it produces are synthetic and mean nothing.
    """
    import hashlib
    import random

    import numpy as np

    sentences = [
        "People climb because the summit gives the day a shape.",
        "Altitude strips a week down to rope, weather and breath.",
        "The mountain refuses to care, and that refusal is restful.",
        "Risk sharpens attention in a way the valley never does.",
        "A rope team is a small society with one honest rule.",
        "The descent is where the real accounting happens.",
    ]

    def fake_chat(messages: list[dict]) -> tuple[str, float]:
        loaded = sum(len(m["content"]) for m in messages)
        rng = random.Random(loaded * 7919 + random.randint(0, 10_000))
        # A longer, more structured layer narrows what the stand-in model says.
        spread = max(2, 6 - loaded // 400)
        picks = rng.sample(sentences[:spread] or sentences[:2], k=min(3, spread))
        return " ".join(picks), 1.0

    def fake_embed(texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            out.append(rng.normal(size=32).tolist())
        return out

    ce.chat = fake_chat
    ce.embed_texts = fake_embed


def fire_volley(label: str, control_form: str, test_form: str,
                n_trials: int, mode: str) -> dict:
    print(f"  → {label}  ({control_form} vs {test_form})", flush=True)
    t0 = time.time()
    run = ce.run_experiment(
        prompt=PROMPT,
        knowledge_layer=KNOWLEDGE,
        n_trials=n_trials,
        injection_mode=mode,
        knowledge_form=test_form,
        control_knowledge_form=control_form,
    )
    data = {
        "control_trials": [t.__dict__ for t in run.control_trials],
        "test_trials": [t.__dict__ for t in run.test_trials],
    }
    comparison = ca.compare_groups(data["control_trials"], data["test_trials"])
    return {
        "label": label,
        "control_form": control_form,
        "test_form": test_form,
        "injection_mode": mode,
        "n_trials": n_trials,
        "seconds": round(time.time() - t0, 1),
        "control_chars": len(run.control_layer),
        "test_chars": len(run.test_layer),
        **comparison,
    }


def _pct(ratio: float | None) -> str:
    """Dispersion change as a signed percentage — negative means a tighter landing zone."""
    if ratio is None:
        return "—"
    return f"{(ratio - 1) * 100:+.1f} %".replace("-", "−")


def write_report(results: list[dict], stats: dict, path: Path, dry_run: bool) -> Path:
    lines = [
        "## Ce qu'une connaissance *structurée* apporte au modèle",
        "",
    ]
    if dry_run:
        lines += ["> ⚠️ **Tir à blanc** — modèle et embeddings simulés. "
                  "Les chiffres ci-dessous ne valent rien, seul le dispositif est validé.", ""]
    lines += [
        f"Même prompt, mêmes faits, même mode d'injection (`{results[0]['injection_mode']}`). "
        f"Seule la *forme* de la couche de connaissance change. "
        f"{results[0]['n_trials']} essais par bras.",
        "",
        f"L'extracteur lit {stats['n_claims']} affirmations dans la prose et en tire une "
        f"taxonomie de {stats.get('graph', {}).get('n_nodes', 0)} concepts et "
        f"{stats.get('graph', {}).get('n_edges', 0)} arêtes, toutes de la même relation "
        f"`sousConceptDe` (du spécifique vers le général), "
        f"{'extraites par ' + stats['graph']['model'] if stats.get('graph', {}).get('source') == 'llm' else 'lues par l’extracteur déterministe (repli : pas de modèle joignable)'}. "
        f"Sujet extrait : **{stats['subject']}**. "
        f"Le bras test n'est chargé que de ces arêtes : les phrases d'origine ne "
        f"l'accompagnent pas.",
        "",
        "### Résultats",
        "",
        "| Volée | Bras contrôle | Bras test | Ratio de dispersion | Resserrement | p-value | Δ centroïde (cos) |",
        "|---|---|---|:---:|:---:|:---:|:---:|",
    ]
    for r in results:
        ratio = r["dispersion_ratio"]
        lines.append(
            f"| **{r['label']}** | `{r['control_form']}` | `{r['test_form']}` | "
            f"{ratio:.3f} | {_pct(ratio)} | {r['mann_whitney_pvalue']:.4f} | "
            f"{r['centroid_shift_cosine']:.3f} |"
        )

    lines += [
        "",
        "### Les deux formes en jeu",
        "",
    ]
    for form_id in ("prose", ks.TEST_ARM_FORM):
        label = ks.STRUCTURE_FORMS[form_id]
        rendered = ks.structure_knowledge(KNOWLEDGE, form_id)
        preview = rendered if len(rendered) < 700 else rendered[:700] + " …"
        lines += [f"**{label}** (`{form_id}`, {len(rendered)} caractères)", "",
                  "```", preview, "```", ""]

    lines += [
        "### Lecture",
        "",
        "Les deux premières volées mesurent ce que la *connaissance* apporte — c'est la "
        "mesure historique de Canon Ball, prose puis graphe contre un bras nu. La dernière "
        "mesure ce que la *structure* ajoute par-dessus : le bras de contrôle porte déjà les "
        "mêmes faits en prose, donc tout resserrement restant est imputable au graphe seul.",
        "",
    ]

    path.write_text("\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=16, help="trials per arm (default 16)")
    parser.add_argument("--mode", default="template", choices=list(ce.INJECTION_MODES),
                        help="injection mode held constant across volleys")
    parser.add_argument("--out", default="structure_results.md", help="report path")
    parser.add_argument("--dry-run", action="store_true",
                        help="stub the model and the embedder — no API key, no network")
    args = parser.parse_args()

    if args.dry_run:
        _install_dry_run_stubs()
        print("Dry run: model and embedder are stand-ins.\n", flush=True)

    stats = ks.structure_stats(KNOWLEDGE, ks.TEST_ARM_FORM)
    graph = stats.get("graph", {})
    print(f"Extractor [{graph.get('source', 'rules')}"
          f"{' · ' + graph['model'] if graph.get('source') == 'llm' else ''}]: "
          f"{stats['n_claims']} claims → {graph.get('n_nodes', 0)} nodes, "
          f"{graph.get('n_edges', 0)} edges, subject '{stats['subject']}', "
          f"relations {graph.get('relations', stats['relations'])}, "
          f"edges-only rendering (verbatim={stats['claims_preserved']})\n", flush=True)

    print(f"Firing {len(VOLLEYS)} volleys × {args.n * 2} shots, mode '{args.mode}':", flush=True)
    results = [fire_volley(label, ctrl, test, args.n, args.mode)
               for label, ctrl, test in VOLLEYS]

    out = write_report(results, stats, Path(args.out), args.dry_run)
    Path("results").mkdir(exist_ok=True)
    Path("results/structure_study.json").write_text(json.dumps(results, indent=2, default=float))

    print(f"\nReport  → {out}")
    print("Raw     → results/structure_study.json")
    for r in results:
        print(f"  {r['label']:<24} ratio {r['dispersion_ratio']:.3f}  "
              f"p {r['mann_whitney_pvalue']:.4f}")


if __name__ == "__main__":
    main()
