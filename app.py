"""
Canon Ball — Streamlit Frontend
Measuring holism: where does the ball land with and without a knowledge layer?
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import json
import subprocess
import time
from pathlib import Path

from experiment import run_experiment, save_experiment, load_experiment
from analysis import full_analysis


st.set_page_config(page_title="Canon Ball", page_icon="🎯", layout="wide")

st.title("Canon Ball")
st.markdown("*Measuring what a knowledge layer adds to an LLM — deterministically.*")

# --- Sidebar: Experiment Configuration ---
with st.sidebar:
    st.header("Experiment Setup")

    prompt = st.text_area(
        "Prompt (the throw)",
        value='Tu vas m\'aider à préparer la course d\'alpinisme "les arêtes du Gerbier" situées dans le Vercors',
        height=100
    )

    knowledge_layer = st.text_area(
        "Knowledge Layer (the launching ramp)",
        value="""# Definition — Alpine Climbing
Source: Wikidata (Q1759504 — Alpine climbing / Q36908 — Alpinism)

An **alpine climbing route** (course d'alpinisme) is a type of climbing practiced in high mountains.
It is a sub-discipline of alpinism (mountain sport, outdoor recreation),
itself related to climbing in the broad sense.

## Included Disciplines
- Glacier climbing (Q1148495)
- Mixed climbing — rock and ice (Q1940865)
- Rock climbing (Q1154336)
- Alpine style — self-sufficient ascent, without porters or fixed camps (Q1203592)

## Characteristic Equipment
- Ice axe, traction ice axe
- Crampons
- Ice screws
- Climbing gear (ropes, cams, friends)

## Practitioners
Alpine climbing routes are led by **alpinists** (Q9149093)
and supervised by **high mountain guides** (Q819677).""",
        height=250
    )

    n_trials = st.slider("Number of trials per group", 3, 20, 12)

    run_btn = st.button("🚀 Launch Experiment", type="primary", use_container_width=True)

# --- Main area ---
results_path = Path("results/experiment.json")
analysis_path = Path("results/analysis.json")

CANNON_FRAMES = [
    # Frame 0: idle
    r"""
          __
         /  \
    ____/    \____
   |              |        ___
   |   CANON      |=======[   )
   |   BALL       |=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
    # Frame 1: fuse lit
    r"""
        * *
          __
         /  \
    ____/    \____
   |              |        ___
   |   CANON    ~*|=======[   )
   |   BALL    ~* |=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
    # Frame 2: BOOM
    r"""
      \  |  /
       \ | /
        \|/
          __        *  BOOM!
         /  \      * *
    ____/    \____ *
   |              |  *     ___
   |   CANON      |==●==>[   )
   |   BALL       |=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
    # Frame 3: ball in flight
    r"""
                              ●
          __                .
         /  \             .
    ____/    \____      .
   |              |   .    ___
   |   CANON      |=======[   )
   |   BALL    ~~~|=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
    # Frame 4: ball arcing
    r"""
                                    ●  .  .
          __                  .  '
         /  \              . '
    ____/    \____      .
   |              |        ___
   |   CANON      |=======[   )
   |   BALL       |=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
    # Frame 5: ball landing on target
    r"""
          __                          ◎ ● !
         /  \                        /|||\
    ____/    \____                  / ||| \
   |              |        ___    ~~~~~~~~~~~
   |   CANON      |=======[   )    TARGET
   |   BALL       |=======[___)
   |______________|
   /\_/\_/\_/\_/\_/\
    """,
]


def animate_cannon(cannon_placeholder, status_placeholder, frame_idx, msg):
    frame = CANNON_FRAMES[frame_idx % len(CANNON_FRAMES)]
    cannon_placeholder.code(frame, language=None)
    status_placeholder.markdown(f"**{msg}**")


if run_btn:
    cannon_area = st.empty()
    status = st.empty()
    progress_bar = st.progress(0.0)

    def on_progress(pct, msg):
        progress_bar.progress(pct)
        if "Control" in msg:
            trial_num = int(msg.split()[2].split("/")[0])
            frame = trial_num % len(CANNON_FRAMES)
        elif "Test" in msg:
            trial_num = int(msg.split()[2].split("/")[0])
            frame = (trial_num + 3) % len(CANNON_FRAMES)
        else:
            frame = 0
        animate_cannon(cannon_area, status, frame, msg)

    animate_cannon(cannon_area, status, 0, "Loading the cannon...")
    time.sleep(0.5)
    animate_cannon(cannon_area, status, 1, "Lighting the fuse...")
    time.sleep(0.5)

    experiment = run_experiment(prompt, knowledge_layer, n_trials, progress_callback=on_progress)
    save_experiment(experiment)

    animate_cannon(cannon_area, status, 5, "Analyzing where the balls landed...")
    data = load_experiment()
    results = full_analysis(data)

    with open("results/analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    progress_bar.progress(1.0)
    status.markdown("**All shots fired! Results ready.**")
    time.sleep(1)
    cannon_area.empty()
    st.rerun()

if analysis_path.exists() and results_path.exists():
    data = load_experiment()
    results = json.loads(analysis_path.read_text())

    st.header("Where did the ball land?")

    # --- Semantic Space Map ---
    proj = results["projection"]

    fig = go.Figure()

    ctrl_pts = np.array(proj["control_points"])
    test_pts = np.array(proj["test_points"])
    ctrl_centroids = np.array(proj["control_centroids"])
    test_centroids = np.array(proj["test_centroids"])

    fig.add_trace(go.Scatter(
        x=ctrl_pts[:, 0], y=ctrl_pts[:, 1],
        mode="markers", name="Control (no knowledge layer)",
        marker=dict(size=5, color="rgba(99,110,250,0.4)", symbol="circle"),
        text=results.get("control_labels", []),
        hoverinfo="text"
    ))

    fig.add_trace(go.Scatter(
        x=test_pts[:, 0], y=test_pts[:, 1],
        mode="markers", name="Test (with knowledge layer)",
        marker=dict(size=5, color="rgba(239,85,59,0.4)", symbol="diamond"),
        text=results.get("test_labels", []),
        hoverinfo="text"
    ))

    fig.add_trace(go.Scatter(
        x=ctrl_centroids[:, 0], y=ctrl_centroids[:, 1],
        mode="markers", name="Control centroids (ball landing spots)",
        marker=dict(size=14, color="rgb(99,110,250)", symbol="circle",
                    line=dict(width=2, color="white")),
        text=[f"Control trial {i}" for i in range(len(ctrl_centroids))],
        hoverinfo="text"
    ))

    fig.add_trace(go.Scatter(
        x=test_centroids[:, 0], y=test_centroids[:, 1],
        mode="markers", name="Test centroids (ball landing spots)",
        marker=dict(size=14, color="rgb(239,85,59)", symbol="diamond",
                    line=dict(width=2, color="white")),
        text=[f"Test trial {i}" for i in range(len(test_centroids))],
        hoverinfo="text"
    ))

    fig.update_layout(
        title="Semantic Space — Where the Ball Lands",
        xaxis_title="UMAP-1", yaxis_title="UMAP-2",
        height=600,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Metrics ---
    st.header("Precision Metrics")
    comp = results["comparison"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Control Dispersion",
            f"{comp['control_mean_dispersion']:.4f}",
            help="Average distance of each trial's centroid from the group center (no knowledge layer)"
        )
    with col2:
        st.metric(
            "Test Dispersion",
            f"{comp['test_mean_dispersion']:.4f}",
            delta=f"{(comp['dispersion_ratio'] - 1) * 100:+.1f}%" if comp['dispersion_ratio'] else "N/A",
            delta_color="inverse",
            help="Average distance of each trial's centroid from the group center (with knowledge layer)"
        )
    with col3:
        st.metric(
            "Centroid Shift (cosine)",
            f"{comp['centroid_shift_cosine']:.4f}",
            help="How far apart the two group centers are — the knowledge layer's 'steering' effect"
        )

    col1, col2 = st.columns(2)
    with col1:
        sig = "✅ Significant" if comp["mann_whitney_pvalue"] < 0.05 else "❌ Not significant"
        st.metric("Mann-Whitney p-value", f"{comp['mann_whitney_pvalue']:.4f}")
        st.caption(f"{sig} (α=0.05) — tests whether dispersion differs between groups")
    with col2:
        ctrl_d = results["control_dispersion"]
        test_d = results["test_dispersion"]
        st.metric("Control pairwise cosine", f"{results['control_pairwise']['mean_pairwise_cosine']:.4f}")
        st.metric("Test pairwise cosine", f"{results['test_pairwise']['mean_pairwise_cosine']:.4f}")

    # --- Interpretation ---
    st.header("Interpretation")

    ratio = comp.get("dispersion_ratio")
    if ratio and ratio < 1:
        st.success(f"""**The knowledge layer tightens the landing zone.**
        Test dispersion is {(1-ratio)*100:.1f}% smaller than control.
        The launching ramp works — outputs are more semantically consistent.""")
    elif ratio and ratio > 1:
        st.warning(f"""**The knowledge layer widens the landing zone.**
        Test dispersion is {(ratio-1)*100:.1f}% larger than control.
        The knowledge layer may be introducing more diverse semantic directions.""")
    else:
        st.info("Dispersion is approximately equal between groups.")

    if comp["centroid_shift_cosine"] > 0.01:
        st.info(f"""**The knowledge layer shifts where the ball lands.**
        The cosine distance between group centers is {comp['centroid_shift_cosine']:.4f}.
        This is the 'steering' effect — the ramp points the ball in a different direction.""")

    # --- Raw outputs viewer ---
    with st.expander("View raw outputs"):
        tab1, tab2 = st.tabs(["Control Trials", "Test Trials"])
        with tab1:
            for t in data["control_trials"]:
                st.markdown(f"**Trial {t['trial_index']}** ({t['latency_ms']:.0f}ms)")
                st.text(t["raw_output"][:500])
                st.divider()
        with tab2:
            for t in data["test_trials"]:
                st.markdown(f"**Trial {t['trial_index']}** ({t['latency_ms']:.0f}ms)")
                st.text(t["raw_output"][:500])
                st.divider()

    # --- Quarto Report ---
    st.header("Generate Report")
    if st.button("📄 Render Quarto Report"):
        with st.spinner("Rendering..."):
            result = subprocess.run(
                ["quarto", "render", "report.qmd", "--to", "html"],
                capture_output=True, text=True,
                cwd=str(Path(__file__).parent)
            )
            if result.returncode == 0:
                st.success("Report rendered! Open `report.html`")
            else:
                st.error(f"Quarto error: {result.stderr}")

else:
    st.info("Configure your experiment in the sidebar and click **Launch Experiment** to begin.")

    st.markdown("""
    ### How it works

    1. **Control trials**: The prompt is sent to the LLM with no system prompt, repeated N times
    2. **Test trials**: The same prompt is sent with your knowledge layer as the system prompt
    3. **Embedding**: Each output is chunked and embedded into a 1024-dim semantic space (bge-m3)
    4. **Projection**: UMAP reduces the space to 2D for visualization
    5. **Measurement**: We compare the dispersion (landing zone size) and centroid shift between groups

    A tighter landing zone in the test group = the knowledge layer acts as a precision-improving launching ramp.
    """)
