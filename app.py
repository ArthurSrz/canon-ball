"""
Canon Ball — Streamlit Frontend
Measuring holism: where does the ball land with and without a knowledge layer?
Uses the scientific instrument UI from Claude Design.
"""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import json
import time
from pathlib import Path

from canon_experiment import run_experiment, save_experiment, load_experiment
from canon_analysis import full_analysis


st.set_page_config(page_title="Canon Ball", page_icon="🎯", layout="wide",
                   initial_sidebar_state="expanded")

# Hide default Streamlit chrome for immersive UI
st.markdown("""<style>
#MainMenu, footer, header, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebar"] { background: #0c1014; }
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] .stTextArea label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] h2 { color: #b8c2cf !important; }
[data-testid="stSidebar"] .stTextArea textarea {
    background: #11161c; border-color: rgba(180,200,230,0.22); color: #e8edf3;
    font-family: "JetBrains Mono", monospace; font-size: 11.5px;
}
section[data-testid="stSidebar"] { border-right: 1px solid rgba(180,200,230,0.12); }
.stApp { background: #07090c; }
</style>""", unsafe_allow_html=True)

# --- Sidebar: Experiment Configuration ---
with st.sidebar:
    st.markdown("### Experiment Setup")

    prompt = st.text_area(
        "Prompt · the throw",
        value='Tu vas m\'aider à préparer la course d\'alpinisme "les arêtes du Gerbier" situées dans le Vercors',
        height=80
    )

    knowledge_layer = st.text_area(
        "Knowledge layer · the ramp",
        value="""# Definition — Alpine Climbing
Source: Wikidata (Q1759504 — Alpine climbing / Q36908 — Alpinism)

An **alpine climbing route** (course d'alpinisme) is a type of climbing
practiced in high mountains. It is a sub-discipline of alpinism.

## Equipment
- Ice axe, crampons, ice screws
- Climbing gear (ropes, cams, friends)

## Practitioners
Alpine climbing routes are led by **alpinists** (Q9149093)
and supervised by **high mountain guides** (Q819677).""",
        height=200
    )

    n_trials = st.slider("Trials per group", 3, 20, 12)
    run_btn = st.button("Fire experiment", type="primary", use_container_width=True)

    # Progress lives in sidebar, right below the button
    sidebar_progress = st.empty()
    sidebar_status = st.empty()

# --- Run experiment ---
results_path = Path("results/experiment.json")
analysis_path = Path("results/analysis.json")

def cannon_animation_html(shot_count, total_shots, current_msg, progress_pct):
    """Generate the cannon firing overlay as self-contained HTML."""
    import random
    shots_js = []
    for i in range(shot_count):
        kind = "control" if i < total_shots // 2 else "test"
        spread = 70 if kind == "control" else 38
        dx = random.uniform(-spread, spread)
        dy = random.uniform(-spread, spread)
        shots_js.append(f'{{"kind":"{kind}","dx":{dx:.1f},"dy":{dy:.1f},"idx":{i}}}')
    shots_json = "[" + ",".join(shots_js) + "]"

    return f"""<!doctype html>
<html><head>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Fraunces:ital,wght@1,400;1,500&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; background:#07090c; overflow:hidden; }}
.cannon-stage {{
  position:relative; width:100%; height:100vh;
  border:1px solid rgba(180,200,230,0.12);
  background: radial-gradient(circle at 50% 90%, rgba(74,214,200,0.05), transparent 60%), #0c1014;
  overflow:hidden;
}}
.cannon-readout {{
  position:absolute; top:18px; left:18px;
  font-family:"JetBrains Mono",monospace; font-size:10.5px;
  letter-spacing:0.14em; text-transform:uppercase; color:#8590a0;
  display:flex; flex-direction:column; gap:4px;
}}
.cannon-readout b {{ color:#e8edf3; font-weight:500; }}
.live {{ display:inline-flex; align-items:center; gap:6px; }}
.dot {{ width:6px; height:6px; border-radius:50%; background:#ff5d6c;
  box-shadow:0 0 8px #ff5d6c; animation:pulse 1s ease-in-out infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }} }}
.pbar {{
  position:absolute; bottom:18px; left:18px; right:18px; height:22px;
  display:flex; align-items:center; gap:12px;
}}
.track {{ flex:1; height:2px; background:rgba(180,200,230,0.22); border-radius:2px; position:relative; }}
.fill {{ position:absolute; inset:0 auto 0 0; background:#4ad6c8;
  box-shadow:0 0 8px rgba(74,214,200,0.55); border-radius:2px;
  width:{progress_pct*100:.1f}%; transition:width 300ms linear; }}
.pct {{ font-family:"JetBrains Mono",monospace; font-size:11px;
  font-variant-numeric:tabular-nums; color:#b8c2cf; min-width:40px; text-align:right; }}
</style>
</head><body>
<div class="cannon-stage">
<svg viewBox="0 0 1100 619" preserveAspectRatio="xMidYMid meet" style="position:absolute;inset:0;width:100%;height:100%">
  <defs>
    <pattern id="cgrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(120,200,255,0.06)" stroke-width="0.5"/>
    </pattern>
    <pattern id="cgrid-major" width="200" height="200" patternUnits="userSpaceOnUse">
      <path d="M 200 0 L 0 0 0 200" fill="none" stroke="rgba(120,200,255,0.12)" stroke-width="0.6"/>
    </pattern>
    <radialGradient id="muzzle" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="rgba(255,200,100,1)"/>
      <stop offset="40%" stop-color="rgba(255,140,60,0.6)"/>
      <stop offset="100%" stop-color="rgba(255,140,60,0)"/>
    </radialGradient>
    <radialGradient id="ctrlGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="rgba(255,181,71,0.5)"/>
      <stop offset="100%" stop-color="rgba(255,181,71,0)"/>
    </radialGradient>
    <radialGradient id="testGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="rgba(74,214,200,0.5)"/>
      <stop offset="100%" stop-color="rgba(74,214,200,0)"/>
    </radialGradient>
  </defs>

  <rect width="1100" height="619" fill="url(#cgrid)"/>
  <rect width="1100" height="619" fill="url(#cgrid-major)"/>

  <!-- Semantic surface horizon -->
  <line x1="0" y1="539" x2="1100" y2="539" stroke="rgba(180,200,230,0.18)" stroke-dasharray="2 6"/>
  <text x="20" y="531" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(138,144,160,0.6)" letter-spacing="0.14em">SEMANTIC SURFACE</text>

  <!-- Control target -->
  <circle cx="820" cy="399" r="80" fill="url(#ctrlGlow)"/>
  <circle cx="820" cy="399" r="60" fill="none" stroke="rgba(255,181,71,0.25)" stroke-width="0.8" stroke-dasharray="3 4"/>
  <circle cx="820" cy="399" r="40" fill="none" stroke="rgba(255,181,71,0.3)" stroke-width="0.8" stroke-dasharray="3 4"/>
  <circle cx="820" cy="399" r="3" fill="rgba(255,181,71,0.9)"/>
  <text x="820" y="499" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(255,181,71,0.7)" letter-spacing="0.14em">CONTROL · ∅</text>

  <!-- Test target -->
  <circle cx="920" cy="339" r="60" fill="url(#testGlow)"/>
  <circle cx="920" cy="339" r="42" fill="none" stroke="rgba(74,214,200,0.3)" stroke-width="0.8" stroke-dasharray="3 4"/>
  <circle cx="920" cy="339" r="24" fill="none" stroke="rgba(74,214,200,0.4)" stroke-width="0.8" stroke-dasharray="3 4"/>
  <circle cx="920" cy="339" r="3" fill="rgba(74,214,200,0.9)"/>
  <text x="920" y="419" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(74,214,200,0.85)" letter-spacing="0.14em">TEST · KL</text>

  <!-- Cannon -->
  <g transform="translate(140, 439)">
    <rect x="-40" y="-4" width="80" height="40" fill="#1a2230" stroke="rgba(180,200,230,0.3)" stroke-width="0.8"/>
    <circle cx="-22" cy="36" r="14" fill="#1a2230" stroke="rgba(180,200,230,0.4)" stroke-width="0.8"/>
    <circle cx="-22" cy="36" r="3" fill="rgba(180,200,230,0.4)"/>
    <circle cx="22" cy="36" r="14" fill="#1a2230" stroke="rgba(180,200,230,0.4)" stroke-width="0.8"/>
    <circle cx="22" cy="36" r="3" fill="rgba(180,200,230,0.4)"/>
    <path d="M -40 36 L 40 36" stroke="rgba(180,200,230,0.3)" stroke-width="1"/>
    <g transform="rotate(-12)">
      <rect x="-10" y="-14" width="92" height="20" rx="2" fill="#0e1620" stroke="rgba(74,214,200,0.5)" stroke-width="0.8"/>
      <rect x="78" y="-16" width="6" height="24" rx="1" fill="#0e1620" stroke="rgba(74,214,200,0.6)" stroke-width="0.8"/>
      <circle cx="0" cy="-4" r="3" fill="#1a2230" stroke="rgba(180,200,230,0.5)" stroke-width="0.7"/>
      <line x1="20" y1="-14" x2="20" y2="-22" stroke="rgba(74,214,200,0.6)" stroke-width="0.6"/>
      <circle cx="20" cy="-23" r="1.4" fill="rgba(74,214,200,0.8)"/>
      <circle cx="86" cy="-4" r="22" fill="url(#muzzle)" opacity="0.8">
        <animate attributeName="opacity" values="0.8;0;0.8" dur="0.8s" repeatCount="indefinite"/>
      </circle>
    </g>
    <text x="0" y="22" text-anchor="middle" font-family="Fraunces,serif" font-style="italic" font-size="11" fill="rgba(180,200,230,0.8)">Canon</text>
  </g>

  <!-- Channel labels -->
  <text x="20" y="40" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(90,100,115,0.9)" letter-spacing="0.14em">CH1 · CONTROL</text>
  <text x="20" y="56" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(255,181,71,0.7)" letter-spacing="0.14em">∅ KNOWLEDGE LAYER</text>
  <text x="20" y="589" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(90,100,115,0.9)" letter-spacing="0.14em">CH2 · TEST</text>
  <text x="20" y="605" font-family="JetBrains Mono,monospace" font-size="10" fill="rgba(74,214,200,0.7)" letter-spacing="0.14em">+ KNOWLEDGE LAYER</text>

  <!-- Range markings -->
  <line x1="275" y1="539" x2="275" y2="535" stroke="rgba(180,200,230,0.3)"/>
  <text x="275" y="553" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="rgba(90,100,115,0.8)">25m</text>
  <line x1="550" y1="539" x2="550" y2="535" stroke="rgba(180,200,230,0.3)"/>
  <text x="550" y="553" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="rgba(90,100,115,0.8)">50m</text>
  <line x1="825" y1="539" x2="825" y2="535" stroke="rgba(180,200,230,0.3)"/>
  <text x="825" y="553" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="rgba(90,100,115,0.8)">75m</text>

  <!-- Animated trajectories -->
  <script type="text/javascript">
  <![CDATA[
    var shots = {shots_json};
    var svg = document.querySelector('svg');
    var cannonX = 220, cannonY = 433;
    var ctrlX = 820, ctrlY = 399, testX = 920, testY = 339;

    shots.forEach(function(s, i) {{
      var tx = (s.kind === 'control' ? ctrlX : testX) + s.dx;
      var ty = (s.kind === 'control' ? ctrlY : testY) + s.dy;
      var cx = (cannonX + tx) / 2;
      var cy = Math.min(cannonY, ty) - 240;
      var path = 'M ' + cannonX + ' ' + cannonY + ' Q ' + cx + ' ' + cy + ' ' + tx + ' ' + ty;
      var color = s.kind === 'control' ? 'rgba(255,181,71,' : 'rgba(74,214,200,';
      var age = Math.min(1, (shots.length - i) / 6);
      var opacity = (0.6 - age * 0.55).toFixed(3);

      // Trail
      var trail = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      trail.setAttribute('d', path);
      trail.setAttribute('fill', 'none');
      trail.setAttribute('stroke', color + opacity + ')');
      trail.setAttribute('stroke-width', '0.8');
      svg.appendChild(trail);

      // Landing dot
      var dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('cx', tx);
      dot.setAttribute('cy', ty);
      dot.setAttribute('r', '2.5');
      dot.setAttribute('fill', color + '0.85)');
      svg.appendChild(dot);
    }});

    // Active shot animation (last shot)
    if (shots.length > 0) {{
      var s = shots[shots.length - 1];
      var tx = (s.kind === 'control' ? ctrlX : testX) + s.dx;
      var ty = (s.kind === 'control' ? ctrlY : testY) + s.dy;
      var cx = (cannonX + tx) / 2;
      var cy = Math.min(cannonY, ty) - 240;
      var path = 'M ' + cannonX + ' ' + cannonY + ' Q ' + cx + ' ' + cy + ' ' + tx + ' ' + ty;
      var ballColor = s.kind === 'control' ? '#ffb547' : '#4ad6c8';

      var ball = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      ball.setAttribute('r', '4');
      ball.setAttribute('fill', ballColor);
      var anim = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
      anim.setAttribute('dur', '0.7s');
      anim.setAttribute('fill', 'freeze');
      anim.setAttribute('path', path);
      anim.setAttribute('repeatCount', 'indefinite');
      ball.appendChild(anim);
      svg.appendChild(ball);
    }}
  ]]>
  </script>
</svg>

<!-- HUD -->
<div class="cannon-readout">
  <div class="live"><span class="dot"></span> FIRING SEQUENCE · LIVE</div>
  <div>SHOT&nbsp;<b>{str(shot_count).zfill(2)}</b>&nbsp;/&nbsp;<b>{str(total_shots).zfill(2)}</b></div>
  <div>{current_msg}</div>
</div>

<!-- Progress bar -->
<div class="pbar">
  <span class="pct">{int(progress_pct*100):02d}%</span>
  <div class="track"><div class="fill"></div></div>
</div>
</div>
</body></html>"""


if run_btn and not st.session_state.get("running"):
    st.session_state["running"] = True
    cannon_area = st.empty()
    shot_counter = [0]

    with st.sidebar:
        sidebar_progress = st.progress(0.0)
        sidebar_status = st.empty()
        sidebar_status.markdown("**Firing sequence initiated...**")

    with cannon_area.container():
        components.html(
            cannon_animation_html(0, n_trials * 2, "Initializing...", 0.0),
            height=620, scrolling=False
        )

    def on_progress(pct, msg):
        sidebar_progress.progress(pct)
        sidebar_status.markdown(f"**{msg}**")
        shot_counter[0] += 1
        with cannon_area.container():
            components.html(
                cannon_animation_html(shot_counter[0], n_trials * 2, msg, pct),
                height=620, scrolling=False
            )

    try:
        experiment = run_experiment(prompt, knowledge_layer, n_trials, progress_callback=on_progress)
        save_experiment(experiment)

        sidebar_status.markdown("**Analyzing semantic space...**")
        data = load_experiment()
        results = full_analysis(data)

        with open("results/analysis.json", "w") as f:
            json.dump(results, f, indent=2)

        sidebar_progress.progress(1.0)
        sidebar_status.markdown("**Done! Results ready.**")
        time.sleep(1)
        sidebar_progress.empty()
        sidebar_status.empty()
        cannon_area.empty()
    except Exception as e:
        st.error(f"Experiment failed: {e}")
    finally:
        st.session_state["running"] = False

# --- Render results ---
if analysis_path.exists() and results_path.exists():
    data = load_experiment()
    results = json.loads(analysis_path.read_text())

    # Merge projection data into a single object for the JS component
    js_data = json.dumps({
        "projection": results["projection"],
        "comparison": results["comparison"],
        "control_dispersion": results["control_dispersion"],
        "test_dispersion": results["test_dispersion"],
        "control_pairwise": results["control_pairwise"],
        "test_pairwise": results["test_pairwise"],
        "prompt": data["prompt"],
        "knowledge_layer": data["knowledge_layer"],
        "n_trials": data["n_trials"],
        "timestamp": data.get("timestamp", ""),
    })

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Fraunces:ital,wght@1,400;1,500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-0: #07090c; --bg-1: #0c1014; --bg-2: #11161c; --bg-3: #161c24;
  --rule: rgba(180,200,230,0.12); --rule-strong: rgba(180,200,230,0.22);
  --ink-0: #e8edf3; --ink-1: #b8c2cf; --ink-2: #8590a0; --ink-3: #5a6473; --ink-4: #3a424d;
  --control: #ffb547; --control-soft: rgba(255,181,71,0.55);
  --test: #4ad6c8; --test-soft: rgba(74,214,200,0.55);
  --warn: #ff5d6c; --ok: #67e8a4;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --font-sans: "Inter Tight", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: "Fraunces", "Times New Roman", Georgia, serif;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; background:var(--bg-0); color:var(--ink-0);
  font-family:var(--font-sans); font-size:14px; line-height:1.45;
  -webkit-font-smoothing:antialiased; }}
body {{ background: radial-gradient(1400px 700px at 60% 10%, rgba(74,214,200,0.04), transparent 60%),
  radial-gradient(1000px 600px at 0% 90%, rgba(255,181,71,0.03), transparent 60%), var(--bg-0); }}
.tabular {{ font-variant-numeric: tabular-nums; }}
.kicker {{ font-family:var(--font-mono); font-size:10.5px; letter-spacing:0.18em;
  text-transform:uppercase; color:var(--ink-2); }}

.app {{ height:100vh; overflow:hidden; display:flex; flex-direction:column; }}

.topbar {{ display:flex; align-items:center; justify-content:space-between;
  padding:14px 28px; border-bottom:1px solid var(--rule);
  background:rgba(7,9,12,0.85); backdrop-filter:blur(8px); }}
.topbar-left {{ display:flex; align-items:center; gap:18px; }}
.brand {{ display:flex; align-items:center; gap:10px; }}
.brand-mark {{ width:28px; height:28px; border-radius:3px; background:var(--bg-2);
  border:1px solid var(--rule-strong); display:grid; place-items:center; }}
.brand-mark svg {{ width:18px; height:18px; }}
.brand-name {{ font-family:var(--font-display); font-style:italic; font-weight:500;
  font-size:16px; letter-spacing:-0.01em; }}
.crumb {{ font-family:var(--font-mono); font-size:11px; letter-spacing:0.14em;
  text-transform:uppercase; color:var(--ink-3); white-space:nowrap; }}
.crumb b {{ color:var(--ink-1); font-weight:500; }}
.topbar-right {{ display:flex; align-items:center; gap:12px; }}
.status-pill {{ display:inline-flex; align-items:center; gap:8px; padding:5px 10px;
  border:1px solid var(--rule-strong); border-radius:100px;
  font-family:var(--font-mono); font-size:10.5px; letter-spacing:0.14em;
  text-transform:uppercase; color:var(--ink-1); white-space:nowrap; }}
.status-pill .dot {{ width:6px; height:6px; border-radius:50%; background:var(--ok);
  box-shadow:0 0 8px var(--ok); animation:pulse 2s cubic-bezier(.65,0,.35,1) infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }} }}

.stage {{ flex:1; min-height:0; padding:20px 28px 18px; display:flex;
  flex-direction:column; gap:12px; overflow:hidden; }}

.headline {{ display:grid; grid-template-columns:1fr auto; gap:40px; align-items:center; flex-shrink:0; }}
.headline h1 {{ margin:0; font-family:var(--font-display); font-style:italic;
  font-weight:400; font-size:clamp(22px,3.2vw,38px); line-height:1.1; letter-spacing:-0.02em; }}
.headline h1 .accent {{ font-family:var(--font-sans); font-style:normal;
  font-weight:600; color:var(--test); }}
.headline-meta {{ display:flex; gap:24px; align-items:end; }}
.metric-inline {{ display:flex; flex-direction:column; gap:2px; }}
.metric-inline .kicker {{ font-size:9.5px; white-space:nowrap; }}
.metric-inline .val {{ font-family:var(--font-mono); font-variant-numeric:tabular-nums;
  font-size:19px; font-weight:500; line-height:1; letter-spacing:-0.01em; margin-top:4px; }}
.metric-inline .val.ok {{ color:var(--ok); }}
.metric-inline .val.test-c {{ color:var(--test); }}
.metric-inline .delta {{ font-family:var(--font-mono); font-size:10.5px; color:var(--ink-2); margin-top:4px; }}
.metric-inline .delta.dn {{ color:var(--ok); }}

.plot-frame {{ position:relative;
  background: radial-gradient(circle at 50% 30%, rgba(74,214,200,0.04), transparent 65%), var(--bg-1);
  border:1px solid var(--rule); border-radius:4px; overflow:hidden;
  flex:1 1 0; min-height:0; width:100%; height:100%; display:block; }}
.plot-frame svg {{ display:block; width:100%; height:100%; }}
.plot-controls {{ position:absolute; top:14px; right:14px; display:flex; gap:4px;
  background:rgba(7,9,12,0.75); backdrop-filter:blur(8px);
  border:1px solid var(--rule); border-radius:4px; padding:4px; z-index:5; }}
.plot-toggle {{ font-family:var(--font-mono); font-size:10px; letter-spacing:0.1em;
  text-transform:uppercase; background:transparent; border:none; color:var(--ink-2);
  padding:6px 10px; cursor:pointer; border-radius:2px; white-space:nowrap; }}
.plot-toggle:hover {{ color:var(--ink-0); }}
.plot-toggle.active {{ background:var(--bg-3); color:var(--ink-0); }}
.plot-corner {{ position:absolute; font-family:var(--font-mono); font-size:10px;
  color:var(--ink-3); letter-spacing:0.12em; text-transform:uppercase; pointer-events:none; }}
.plot-corner.tl {{ top:14px; left:90px; white-space:nowrap; }}
.plot-corner.br {{ bottom:14px; right:16px; color:var(--ink-2); }}
.legend-strip {{ display:flex; align-items:center; gap:18px; padding:0 16px;
  font-family:var(--font-mono); font-size:10.5px; letter-spacing:0.12em;
  text-transform:uppercase; color:var(--ink-2); flex-shrink:0; white-space:nowrap; }}
.legend-strip .lg-row {{ display:flex; align-items:center; gap:6px; color:var(--ink-1); }}
.legend-strip .swatch {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
.legend-strip .swatch.control {{ background:var(--control); box-shadow:0 0 6px var(--control-soft); }}
.legend-strip .swatch.test {{ background:var(--test); box-shadow:0 0 6px var(--test-soft); }}
.plot-frame .tick text {{ font-family:var(--font-mono); font-size:9px; fill:var(--ink-3); }}

.footstrip {{ display:grid; grid-template-columns:2fr 1fr 1fr 1fr; gap:0;
  border:1px solid var(--rule); border-radius:4px; background:var(--bg-1); flex-shrink:0; }}
.footstrip > div {{ padding:12px 16px; border-right:1px solid var(--rule); }}
.footstrip > div:last-child {{ border-right:none; }}
.foot-stat .k {{ font-family:var(--font-mono); font-size:10px; letter-spacing:0.14em;
  text-transform:uppercase; color:var(--ink-3); }}
.foot-stat .v {{ font-family:var(--font-mono); font-variant-numeric:tabular-nums;
  font-size:16px; font-weight:500; margin-top:3px; letter-spacing:-0.01em; }}
.foot-stat .v.ok {{ color:var(--ok); }}
.foot-stat .v.test-c {{ color:var(--test); }}
.foot-stat .sub {{ font-family:var(--font-mono); font-size:10.5px; color:var(--ink-3); margin-top:3px; }}
.foot-stat .sub b {{ color:var(--ink-1); font-weight:500; }}
.foot-experiment {{ display:flex; flex-direction:column; gap:6px; }}
.foot-experiment .row {{ display:flex; align-items:baseline; gap:8px;
  font-family:var(--font-mono); font-size:11.5px; color:var(--ink-1); white-space:nowrap; overflow:hidden; }}
.foot-experiment .row > span:last-child {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }}
.foot-experiment .row .k {{ color:var(--ink-3); letter-spacing:0.1em; font-size:10px;
  text-transform:uppercase; min-width:64px; }}

.point-tip {{ position:absolute; pointer-events:none; background:var(--bg-3);
  border:1px solid var(--rule-strong); border-radius:3px; padding:8px 10px;
  font-family:var(--font-mono); font-size:11px; color:var(--ink-0); z-index:20;
  box-shadow:0 8px 30px rgba(0,0,0,0.6); max-width:320px; }}
.point-tip .head {{ display:flex; align-items:center; gap:6px; margin-bottom:4px;
  font-size:9.5px; letter-spacing:0.14em; text-transform:uppercase; }}
.point-tip .head .swatch {{ width:7px; height:7px; border-radius:50%; }}
.point-tip .body {{ font-size:11.5px; line-height:1.4; color:var(--ink-1); font-family:var(--font-sans); }}

@media (max-width: 900px) {{
  .headline {{ grid-template-columns:1fr; gap:12px; }}
  .headline-meta {{ flex-wrap:wrap; }}
  .footstrip {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div id="root"></div>
<script src="https://unpkg.com/react@18.3.1/umd/react.production.min.js" crossorigin="anonymous"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js" crossorigin="anonymous"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" crossorigin="anonymous"></script>
<script type="text/babel">
const {{ useState, useEffect, useMemo, useRef }} = React;

const DATA = {js_data};

function SemanticPlot({{ projection, layers, onPointHover }}) {{
  const ref = useRef(null);
  const [size, setSize] = useState({{ w: 1200, h: 600 }});

  useEffect(() => {{
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => {{
      const r = entries[0].contentRect;
      setSize({{ w: r.width, h: r.height }});
    }});
    ro.observe(ref.current);
    return () => ro.disconnect();
  }}, []);

  const all = useMemo(() => {{
    if (!projection) return [];
    return [...(projection.control_points || []), ...(projection.test_points || [])];
  }}, [projection]);

  const bounds = useMemo(() => {{
    if (!all.length) return {{ minX: -10, maxX: 10, minY: -10, maxY: 10 }};
    let minX = Infinity,maxX = -Infinity,minY = Infinity,maxY = -Infinity;
    for (const [x, y] of all) {{
      if (x < minX) minX = x;if (x > maxX) maxX = x;
      if (y < minY) minY = y;if (y > maxY) maxY = y;
    }}
    const padX = (maxX - minX) * 0.08;
    const padY = (maxY - minY) * 0.08;
    return {{ minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY }};
  }}, [all]);

  const padL = 64,padR = 32,padT = 32,padB = 44;
  const W = Math.max(400, size.w);
  const H = Math.max(300, size.h);
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const sx = (x) => padL + (x - bounds.minX) / (bounds.maxX - bounds.minX) * plotW;
  const sy = (y) => padT + plotH - (y - bounds.minY) / (bounds.maxY - bounds.minY) * plotH;

  function ellipse(points) {{
    if (points.length < 2) return null;
    let mx = 0,my = 0;
    for (const [x, y] of points) {{mx += x;my += y;}}
    mx /= points.length;my /= points.length;
    let sxx = 0,sxy = 0,syy = 0;
    for (const [x, y] of points) {{
      const dx = x - mx,dy = y - my;
      sxx += dx * dx;sxy += dx * dy;syy += dy * dy;
    }}
    sxx /= points.length;sxy /= points.length;syy /= points.length;
    const tr = sxx + syy;
    const det = sxx * syy - sxy * sxy;
    const eig = Math.sqrt(Math.max(0, tr * tr / 4 - det));
    const l1 = tr / 2 + eig,l2 = tr / 2 - eig;
    const a = Math.sqrt(Math.max(0, l1)) * 2.0;
    const b = Math.sqrt(Math.max(0, l2)) * 2.0;
    const angle = Math.atan2(2 * sxy, sxx - syy) / 2;
    return {{ mx, my, a, b, angle }};
  }}

  const ctrlEllipse = useMemo(() => projection ? ellipse(projection.control_centroids) : null, [projection]);
  const testEllipse = useMemo(() => projection ? ellipse(projection.test_centroids) : null, [projection]);

  function ePack(e) {{
    if (!e) return null;
    return {{ cx: sx(e.mx), cy: sy(e.my), deg: -(e.angle * 180) / Math.PI,
      rx: e.a / (bounds.maxX - bounds.minX) * plotW,
      ry: e.b / (bounds.maxY - bounds.minY) * plotH }};
  }}
  const cE = ePack(ctrlEllipse),tE = ePack(testEllipse);

  function ticks(min, max, count = 8) {{
    const arr = [];
    for (let i = 0; i <= count; i++) arr.push(min + (max - min) / count * i);
    return arr;
  }}
  const xt = ticks(bounds.minX, bounds.maxX, 8);
  const yt = ticks(bounds.minY, bounds.maxY, 6);

  if (!projection) return <div className="plot-frame" ref={{ref}}></div>;

  const ctrlPts = projection.control_points;
  const testPts = projection.test_points;
  const ctrlC = projection.control_centroids;
  const testC = projection.test_centroids;

  function meanOf(arr) {{
    if (!arr.length) return null;
    let mx = 0,my = 0;
    for (const [x, y] of arr) {{mx += x;my += y;}}
    return [mx / arr.length, my / arr.length];
  }}
  const ctrlMean = meanOf(ctrlC);
  const testMean = meanOf(testC);

  return (
    <div className="plot-frame" ref={{ref}}>
      <svg viewBox={{`0 0 ${{W}} ${{H}}`}} preserveAspectRatio="none">
        <defs>
          <radialGradient id="cFill" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="rgba(255,181,71,0.06)" />
            <stop offset="100%" stopColor="rgba(255,181,71,0)" />
          </radialGradient>
          <radialGradient id="tFill" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="rgba(74,214,200,0.08)" />
            <stop offset="100%" stopColor="rgba(74,214,200,0)" />
          </radialGradient>
          <marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 Z" fill="rgba(232,237,243,0.75)" />
          </marker>
        </defs>

        {{layers.grid &&
        <g>
            {{xt.map((t, i) =>
          <line key={{`x${{i}}`}} x1={{sx(t)}} y1={{padT}} x2={{sx(t)}} y2={{padT + plotH}} stroke="rgba(120,200,255,0.05)" />
          )}}
            {{yt.map((t, i) =>
          <line key={{`y${{i}}`}} x1={{padL}} y1={{sy(t)}} x2={{padL + plotW}} y2={{sy(t)}} stroke="rgba(120,200,255,0.05)" />
          )}}
            <rect x={{padL}} y={{padT}} width={{plotW}} height={{plotH}} fill="none" stroke="rgba(180,200,230,0.18)" />
            <line x1={{sx(0)}} y1={{padT}} x2={{sx(0)}} y2={{padT + plotH}} stroke="rgba(120,200,255,0.12)" strokeDasharray="2 4" />
            <line x1={{padL}} y1={{sy(0)}} x2={{padL + plotW}} y2={{sy(0)}} stroke="rgba(120,200,255,0.12)" strokeDasharray="2 4" />
          </g>
        }}

        <g className="tick">
          {{xt.map((t, i) => <text key={{`tx${{i}}`}} x={{sx(t)}} y={{padT + plotH + 18}} textAnchor="middle">{{t.toFixed(1)}}</text>)}}
          {{yt.map((t, i) => <text key={{`ty${{i}}`}} x={{padL - 10}} y={{sy(t) + 3}} textAnchor="end">{{t.toFixed(1)}}</text>)}}
          <text x={{padL + plotW / 2}} y={{H - 12}} textAnchor="middle" fill="var(--ink-3)" fontFamily="var(--font-mono)" fontSize="10" letterSpacing="0.14em">UMAP·1</text>
          <text x={{18}} y={{padT + plotH / 2}} transform={{`rotate(-90, 18, ${{padT + plotH / 2}})`}} textAnchor="middle" fill="var(--ink-3)" fontFamily="var(--font-mono)" fontSize="10" letterSpacing="0.14em">UMAP·2</text>
        </g>

        {{layers.ellipses && cE &&
        <g transform={{`rotate(${{cE.deg}} ${{cE.cx}} ${{cE.cy}})`}}>
            <ellipse cx={{cE.cx}} cy={{cE.cy}} rx={{cE.rx}} ry={{cE.ry}} fill="url(#cFill)" stroke="rgba(255,181,71,0.5)" strokeWidth="1" strokeDasharray="3 3" />
            <ellipse cx={{cE.cx}} cy={{cE.cy}} rx={{cE.rx * 0.6}} ry={{cE.ry * 0.6}} fill="none" stroke="rgba(255,181,71,0.25)" strokeWidth="0.6" strokeDasharray="2 4" />
          </g>
        }}
        {{layers.ellipses && tE &&
        <g transform={{`rotate(${{tE.deg}} ${{tE.cx}} ${{tE.cy}})`}}>
            <ellipse cx={{tE.cx}} cy={{tE.cy}} rx={{tE.rx}} ry={{tE.ry}} fill="url(#tFill)" stroke="rgba(74,214,200,0.65)" strokeWidth="1" strokeDasharray="3 3" />
            <ellipse cx={{tE.cx}} cy={{tE.cy}} rx={{tE.rx * 0.6}} ry={{tE.ry * 0.6}} fill="none" stroke="rgba(74,214,200,0.4)" strokeWidth="0.6" strokeDasharray="2 4" />
          </g>
        }}

        {{layers.chunks &&
        <g>
            {{ctrlPts.map(([x, y], i) => <circle key={{`c${{i}}`}} cx={{sx(x)}} cy={{sy(y)}} r="1.6" fill="rgba(255,181,71,0.4)" />)}}
            {{testPts.map(([x, y], i) => <circle key={{`t${{i}}`}} cx={{sx(x)}} cy={{sy(y)}} r="1.6" fill="rgba(74,214,200,0.45)" />)}}
          </g>
        }}

        {{layers.shift && ctrlMean && testMean &&
        <g>
            <line x1={{sx(ctrlMean[0])}} y1={{sy(ctrlMean[1])}} x2={{sx(testMean[0])}} y2={{sy(testMean[1])}} stroke="rgba(232,237,243,0.7)" strokeWidth="1.2" markerEnd="url(#arr)" />
            <text x={{(sx(ctrlMean[0]) + sx(testMean[0])) / 2 + 10}} y={{(sy(ctrlMean[1]) + sy(testMean[1])) / 2 - 8}} fontFamily="var(--font-mono)" fontSize="10" fill="rgba(232,237,243,0.75)" letterSpacing="0.1em">Δ centroid</text>
          </g>
        }}

        {{layers.centroids &&
        <g>
            {{ctrlC.map(([x, y], i) =>
          <g key={{`cc${{i}}`}}
          onMouseEnter={{() => onPointHover && onPointHover({{ kind: "control", idx: i, x, y, sx: sx(x), sy: sy(y) }})}}
          onMouseLeave={{() => onPointHover && onPointHover(null)}}
          style={{{{ cursor: "pointer" }}}}>
                <circle cx={{sx(x)}} cy={{sy(y)}} r="6" fill="rgba(255,181,71,0.95)" stroke="var(--bg-1)" strokeWidth="1.5" />
              </g>
          )}}
            {{testC.map(([x, y], i) =>
          <g key={{`tc${{i}}`}}
          onMouseEnter={{() => onPointHover && onPointHover({{ kind: "test", idx: i, x, y, sx: sx(x), sy: sy(y) }})}}
          onMouseLeave={{() => onPointHover && onPointHover(null)}}
          style={{{{ cursor: "pointer" }}}}>
                <rect x={{sx(x) - 5}} y={{sy(y) - 5}} width="10" height="10" fill="rgba(74,214,200,0.95)" stroke="var(--bg-1)" strokeWidth="1.5" transform={{`rotate(45 ${{sx(x)}} ${{sy(y)}})`}} />
              </g>
          )}}
            {{ctrlMean &&
          <g>
                <circle cx={{sx(ctrlMean[0])}} cy={{sy(ctrlMean[1])}} r="13" fill="none" stroke="rgba(255,181,71,0.95)" strokeWidth="1.5" />
                <line x1={{sx(ctrlMean[0]) - 16}} y1={{sy(ctrlMean[1])}} x2={{sx(ctrlMean[0]) + 16}} y2={{sy(ctrlMean[1])}} stroke="rgba(255,181,71,0.95)" strokeWidth="0.8" />
                <line x1={{sx(ctrlMean[0])}} y1={{sy(ctrlMean[1]) - 16}} x2={{sx(ctrlMean[0])}} y2={{sy(ctrlMean[1]) + 16}} stroke="rgba(255,181,71,0.95)" strokeWidth="0.8" />
              </g>
          }}
            {{testMean &&
          <g>
                <circle cx={{sx(testMean[0])}} cy={{sy(testMean[1])}} r="13" fill="none" stroke="rgba(74,214,200,1)" strokeWidth="1.5" />
                <line x1={{sx(testMean[0]) - 16}} y1={{sy(testMean[1])}} x2={{sx(testMean[0]) + 16}} y2={{sy(testMean[1])}} stroke="rgba(74,214,200,1)" strokeWidth="0.8" />
                <line x1={{sx(testMean[0])}} y1={{sy(testMean[1]) - 16}} x2={{sx(testMean[0])}} y2={{sy(testMean[1]) + 16}} stroke="rgba(74,214,200,1)" strokeWidth="0.8" />
              </g>
          }}
          </g>
        }}
      </svg>
    </div>);
}}

function App() {{
  const [hovered, setHovered] = useState(null);
  const [layers, setLayers] = useState({{
    grid: true, chunks: true, centroids: true, ellipses: true, shift: true
  }});

  const projection = DATA.projection;
  const analysis = DATA;

  const verdict = useMemo(() => {{
    const c = analysis.comparison;
    return {{
      ratio: c.dispersion_ratio,
      reduction: (1 - c.dispersion_ratio) * 100,
      pvalue: c.mann_whitney_pvalue,
      shift: c.centroid_shift_cosine,
      sig: c.mann_whitney_pvalue < 0.05,
      tighter: c.dispersion_ratio < 1
    }};
  }}, [analysis]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand">
            <div className="brand-mark">
              <svg viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="9" stroke="#4ad6c8" strokeWidth="1" strokeDasharray="2 2" />
                <circle cx="12" cy="12" r="5" stroke="#ffb547" strokeWidth="1" strokeDasharray="2 2" />
                <circle cx="12" cy="12" r="1.5" fill="#4ad6c8" />
              </svg>
            </div>
            <span className="brand-name">Canon Ball</span>
          </div>
          <span className="crumb">Run <b>EXP·{{DATA.timestamp.replace(/[-:T]/g, '·').slice(0,16)}}</b></span>
          <span className="crumb" style={{{{ color: "var(--ink-3)" }}}}>·</span>
          <span className="crumb">qwen2.5 · bge-m3</span>
        </div>
        <div className="topbar-right">
          <span className="status-pill"><span className="dot"></span>Run complete · {{projection.control_centroids.length}}+{{projection.test_centroids.length}} trials</span>
        </div>
      </header>

      <div className="stage">
        <div className="headline">
          <h1>The knowledge layer <span className="accent">{{verdict.tighter ? `tightens the landing zone by ${{verdict.reduction.toFixed(1)}}%` : `widens the landing zone by ${{Math.abs(verdict.reduction).toFixed(1)}}%`}}</span>{{verdict.sig ? ", with a significant centroid shift." : "."}}</h1>
          <div className="headline-meta">
            <div className="metric-inline">
              <div className="kicker">Dispersion ratio</div>
              <div className="val ok tabular">{{verdict.ratio.toFixed(3)}}</div>
              <div className={{`delta ${{verdict.tighter ? "dn" : ""}}`}}>{{verdict.tighter ? "−" : "+"}}{{Math.abs(verdict.reduction).toFixed(1)}}%</div>
            </div>
            <div className="metric-inline">
              <div className="kicker">p-value</div>
              <div className="val ok tabular">{{verdict.pvalue < 0.0001 ? "<1e-4" : verdict.pvalue.toFixed(4)}}</div>
              <div className="delta dn">{{verdict.sig ? "significant" : "not significant"}}</div>
            </div>
            <div className="metric-inline">
              <div className="kicker">Δ centroid</div>
              <div className="val test-c tabular">{{verdict.shift.toFixed(3)}}</div>
              <div className="delta">cosine</div>
            </div>
          </div>
        </div>

        <div style={{{{ position: "relative", flex: "1 1 0", minHeight: 0, display: "flex" }}}}>
          <SemanticPlot projection={{projection}} layers={{layers}} onPointHover={{setHovered}} />
          <div className="plot-controls">
            {{[["chunks","Chunks"],["centroids","Centroids"],["ellipses","Ellipses"],["shift","Δ vector"],["grid","Grid"]].map(([k, label]) =>
            <button key={{k}} className={{`plot-toggle ${{layers[k] ? "active" : ""}}`}}
            onClick={{() => setLayers((L) => ({{ ...L, [k]: !L[k] }}))}}>{{label}}</button>
            )}}
          </div>
          <div className="plot-corner tl">UMAP·2D · BGE-M3 · 1024d→2d</div>
          <div className="plot-corner br">
            {{hovered ?
            `${{hovered.kind === "control" ? "C" : "T"}}${{String(hovered.idx).padStart(2, "0")}} · (${{hovered.x.toFixed(2)}}, ${{hovered.y.toFixed(2)}})` :
            `${{projection.control_points.length}}+${{projection.test_points.length}} chunks · ${{projection.control_centroids.length}}+${{projection.test_centroids.length}} trials`}}
          </div>
          {{hovered &&
          <div className="point-tip" style={{{{ left: hovered.sx + 14, top: hovered.sy + 14 }}}}>
              <div className="head" style={{{{ color: hovered.kind === "control" ? "var(--control)" : "var(--test)" }}}}>
                <span className="swatch" style={{{{ background: hovered.kind === "control" ? "var(--control)" : "var(--test)" }}}}></span>
                {{hovered.kind === "control" ? "Control" : "Test"}} · trial {{String(hovered.idx).padStart(2, "0")}}
              </div>
              <div className="body">centroid ({{hovered.x.toFixed(3)}}, {{hovered.y.toFixed(3)}})</div>
            </div>
          }}
        </div>

        <div className="legend-strip">
          <span className="lg-row"><span className="swatch control"></span>Control · ∅ KL</span>
          <span className="lg-row"><span className="swatch test"></span>Test · + KL</span>
          <span style={{{{ color: "var(--ink-4)" }}}}>·</span>
          <span>Centroids = trials · Chunks = sentence embeddings</span>
        </div>

        <div className="footstrip">
          <div className="foot-experiment">
            <div className="row"><span className="k">Prompt</span><span style={{{{ color: "var(--ink-1)" }}}}>{{DATA.prompt}}</span></div>
            <div className="row"><span className="k">Layer</span><span style={{{{ color: "var(--ink-1)" }}}}>Wikidata · Alpine Climbing · {{DATA.knowledge_layer.length}}c</span></div>
            <div className="row"><span className="k">Trials</span><span style={{{{ color: "var(--ink-1)" }}}}>{{projection.control_centroids.length}} control · {{projection.test_centroids.length}} test</span></div>
          </div>
          <div className="foot-stat">
            <div className="k">Mean dispersion</div>
            <div className="v ok">{{analysis.comparison.test_mean_dispersion.toFixed(3)}}</div>
            <div className="sub">vs <b>{{analysis.comparison.control_mean_dispersion.toFixed(3)}}</b> control</div>
          </div>
          <div className="foot-stat">
            <div className="k">Pairwise cosine</div>
            <div className="v">{{analysis.test_pairwise.mean_pairwise_cosine.toFixed(3)}}</div>
            <div className="sub">vs <b>{{analysis.control_pairwise.mean_pairwise_cosine.toFixed(3)}}</b> control</div>
          </div>
          <div className="foot-stat">
            <div className="k">Mann–Whitney U</div>
            <div className="v test-c">{{analysis.comparison.mann_whitney_stat.toFixed(0)}}</div>
            <div className="sub">p = <b>{{analysis.comparison.mann_whitney_pvalue.toExponential(2)}}</b></div>
          </div>
        </div>
      </div>
    </div>);
}}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>"""

    components.html(html, height=820, scrolling=False)

else:
    # Empty state
    components.html("""<!doctype html>
<html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Fraunces:ital,wght@1,400;1,500&display=swap" rel="stylesheet">
<style>
body { margin:0; background:#07090c; color:#e8edf3; font-family:"Inter Tight",sans-serif;
  display:grid; place-items:center; height:100vh; text-align:center; }
h1 { font-family:"Fraunces",serif; font-style:italic; font-weight:400;
  font-size:38px; letter-spacing:-0.02em; margin:0 0 12px; }
h1 span { font-family:"Inter Tight",sans-serif; font-style:normal; font-weight:600; color:#4ad6c8; }
p { color:#8590a0; font-family:"JetBrains Mono",monospace; font-size:11px;
  letter-spacing:0.14em; text-transform:uppercase; max-width:500px; line-height:1.8; }
.mark { width:48px; height:48px; margin:0 auto 24px; }
</style>
</head><body>
<div>
  <svg class="mark" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="18" stroke="#4ad6c8" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
    <circle cx="24" cy="24" r="10" stroke="#ffb547" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
    <circle cx="24" cy="24" r="3" fill="#4ad6c8"/>
  </svg>
  <h1>Canon Ball</h1>
  <p>Open the sidebar to configure your experiment.<br/>
  Set a prompt, a knowledge layer, choose trial count, then fire.<br/><br/>
  The semantic scatter will appear here — showing where each ball lands<br/>
  in embedding space, with and without the launching ramp.</p>
</div>
</body></html>""", height=500, scrolling=False)
