"""
Pure HTML/SVG/JS builder functions — no Streamlit dependency.
Extracted from app.py for reuse across pages.
"""

import json


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


def mise_en_abime_html(scene: dict, np_url: str = "") -> str:
    """A triptych, played as three acts:

      ① the prompt discloses vertically down the center (the question);
      ② FORWARD — the attribution graph travels left→right, layer by layer, to a prominent ANSWER;
      ③ BACKWARD — the NLA verbalizations grow leftward as roots (what each word means inside).

    Each act is temporally distinct (narrated by the status line). Self-contained SVG component.
    """
    payload = json.dumps(scene)
    np_js = json.dumps(np_url or "")
    meta = scene.get("meta", {})

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Fraunces:ital,wght@1,400;1,500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-0:#07090c; --bg-2:#11161c; --bg-3:#161c24; --rule:rgba(180,200,230,0.12);
  --ink-0:#e8edf3; --ink-1:#b8c2cf; --ink-2:#8590a0; --ink-3:#5a6473; --ink-4:#3a424d;
  --control:#ffb547; --test:#4ad6c8; --ans:#67e8a4;
  --mono:"JetBrains Mono",monospace; --sans:"Inter Tight",sans-serif; --disp:"Fraunces",serif;
}}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; background:var(--bg-0); color:var(--ink-0); font-family:var(--sans);
  -webkit-font-smoothing:antialiased; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr 1fr; padding:14px 22px 2px; }}
.cols .c {{ font-family:var(--mono); font-size:10px; letter-spacing:0.06em; }}
.cols .l {{ text-align:left;  color:var(--control); }}
.cols .m {{ text-align:center; color:var(--ink-2); }}
.cols .r {{ text-align:right; color:var(--test); }}
.cols .c .n {{ opacity:0.5; }}
.status {{ font-family:var(--mono); font-size:11px; color:var(--ink-1); padding:4px 22px 8px; min-height:16px; }}
.status .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--control);
  margin-right:8px; vertical-align:middle; animation:pulse 1s infinite; }}
.status.done .dot {{ background:var(--ans); animation:none; }}
@keyframes pulse {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.25;}} }}
svg {{ width:100%; height:auto; display:block; }}
.reveal {{ opacity:0; transition:opacity .5s ease; }}
.reveal.in {{ opacity:1; }}
.wlabel {{ font-family:var(--mono); font-weight:500; }}
.wlabel.prompt {{ fill:var(--ink-0); }}
.wlabel.context {{ fill:var(--ink-4); }}
.rootlabel {{ font-family:var(--sans); fill:var(--control); }}
.anstok {{ font-family:var(--disp); font-style:italic; fill:var(--ans); }}
.ansprob {{ font-family:var(--mono); fill:var(--ink-3); }}
.detail {{ font-family:var(--sans); font-size:13px; color:var(--ink-1); line-height:1.5;
  border-left:2px solid var(--ink-4); margin:4px 22px 14px; padding:6px 0 6px 12px; min-height:18px;
  transition:border-color .2s; }}
.detail .lbl {{ font-family:var(--mono); font-size:9px; letter-spacing:0.16em; text-transform:uppercase;
  color:var(--ink-3); display:block; margin-bottom:3px; }}
.foot {{ font-family:var(--mono); font-size:10px; color:var(--ink-3); padding:0 22px 16px; }}
.foot a {{ color:var(--test); text-decoration:none; }} .foot a:hover {{ text-decoration:underline; }}
</style></head>
<body>
<div class="cols">
  <div class="c l"><span class="n">③ backward ◀</span> NLA roots · {meta.get('nla_model','')}</div>
  <div class="c m">① the question</div>
  <div class="c r">forward ▶ ② attribution · {meta.get('attrib_model','')}</div>
</div>
<div class="status" id="status"><span class="dot"></span><span id="stxt">①&nbsp; the question, word by word…</span></div>
<div id="stage"></div>
<div class="detail" id="detail"><span class="lbl">hover</span><span id="dtxt">Hover a root for its full verbalization, or a node for its attribution.</span></div>
<div class="foot" id="foot"></div>
<script>
const S = {payload};
const NP_URL = {np_js};
const NS = "http://www.w3.org/2000/svg";
const words = S.words || [], roots = S.roots || [], tree = (S.tree || {{}});
const tnodes = tree.nodes || [], tlinks = tree.links || [];
const rootByWord = {{}}; roots.forEach(r => rootByWord[r.word_index]=r);

const nW = Math.max(words.length, 1);
const W = 1200;
const rowH = Math.max(30, Math.min(72, Math.round(820 / nW)));
const padY = 54;
const H = Math.max(360, padY*2 + (nW-1)*rowH);
const spineX = Math.round(W*0.36);
const ansX   = W - 96;
const wordY = i => padY + i*rowH;
const maxDepth = Math.max(tree.max_depth || 1, 1);
const treeX = d => spineX + 46 + (d/maxDepth)*(ansX - spineX - 150);

const svg = document.createElementNS(NS,"svg");
svg.setAttribute("viewBox", `0 0 ${{W}} ${{H}}`);
function el(t,a){{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;}}
function detail(label,text,color){{
  document.querySelector('#detail .lbl').textContent=label;
  document.getElementById('dtxt').textContent=text;
  document.getElementById('detail').style.borderLeftColor=color||"var(--ink-4)";
}}

svg.appendChild(el("line",{{x1:spineX,y1:padY-18,x2:spineX,y2:wordY(nW-1)+18,
  stroke:"#3a424d","stroke-width":"1","stroke-dasharray":"2 4"}}));

const cell={{}}; tnodes.forEach(n=>{{const k=n.word_index+"_"+n.depth;(cell[k]=cell[k]||[]).push(n);}});
const pos={{}};
Object.values(cell).forEach(group=>{{const g=group.length;group.forEach((n,k)=>{{
  const spread=Math.min(15,(rowH-6)/Math.max(g,1));
  pos[n.id]={{x:treeX(n.depth),y:wordY(n.word_index)+(k-(g-1)/2)*spread}};
}});}});
const maxInf=Math.max(...tnodes.map(n=>n.influence||0),0.01);

const logits=tnodes.filter(n=>n.type==="logit").sort((a,b)=>(b.prob||0)-(a.prob||0));
const ansY=H/2;
logits.forEach(n=>pos[n.id]={{x:ansX-4,y:ansY+(logits.indexOf(n)-(logits.length-1)/2)*16}});

const linkEl=[];
tlinks.forEach(l=>{{
  const a=pos[l.source],b=pos[l.target]; if(!a||!b) return;
  const mx=(a.x+b.x)/2;
  const p=el("path",{{d:`M ${{a.x}} ${{a.y}} C ${{mx}} ${{a.y}}, ${{mx}} ${{b.y}}, ${{b.x}} ${{b.y}}`,
    fill:"none",stroke:l.weight>=0?"#4ad6c8":"#ff5d6c",
    "stroke-width":(0.3+Math.min(Math.abs(l.weight)/4,1.4)).toFixed(2),"stroke-opacity":"0.14"}});
  p.classList.add("reveal"); p.dataset.draw="1";
  p.dataset.tdepth=(tnodes.find(n=>n.id===l.target)||{{}}).depth||0;
  svg.appendChild(p); linkEl.push(p);
}});

const nodeByDepth={{}};
tnodes.filter(n=>n.type!=="logit").forEach(n=>{{
  const p=pos[n.id]; if(!p) return;
  const isEmb=n.type==="embedding";
  const r=isEmb?4:(2.5+4.5*(n.influence/maxInf));
  const fill=isEmb?"#ffb547":"#11161c";
  const g=el("g",{{class:"reveal"}}); g.style.cursor="pointer";
  const c=el("circle",{{cx:p.x,cy:p.y,r:r,fill:fill,stroke:isEmb?"#ffb547":"#4ad6c8",
    "stroke-width":"1.2","fill-opacity":"0.9"}});
  g.appendChild(c);
  const desc=isEmb?("input token #"+n.ctx_idx):("feature · layer "+n.layer+" · influence "+(n.influence||0).toFixed(2));
  g.addEventListener("mouseenter",()=>{{c.setAttribute("fill","#4ad6c8");detail(n.type||"node",desc,"#4ad6c8");}});
  g.addEventListener("mouseleave",()=>c.setAttribute("fill",fill));
  svg.appendChild(g);
  (nodeByDepth[n.depth]=nodeByDepth[n.depth]||[]).push(g);
}});

const ansG=el("g",{{class:"reveal"}});
ansG.appendChild(el("circle",{{cx:ansX,cy:ansY,r:9,fill:"#67e8a4","fill-opacity":"0.9"}}));
const ansTop=logits[0];
const at=el("text",{{x:ansX-16,y:ansY-12,"text-anchor":"end",class:"anstok","font-size":"19"}});
at.textContent=(ansTop?ansTop.label.replace(/^Output\\s*/,"").replace(/\\s*\\(p=.*$/,""):"answer");
const ap=el("text",{{x:ansX-16,y:ansY+6,"text-anchor":"end",class:"ansprob","font-size":"10"}});
ap.textContent=ansTop?("p="+(ansTop.prob||0).toFixed(2)):"";
const al=el("text",{{x:ansX-16,y:ansY+22,"text-anchor":"end",class:"ansprob","font-size":"9","fill":"#5a6473"}});
al.textContent=logits.slice(1,4).map(n=>n.label.replace(/^Output\\s*/,"").replace(/\\s*\\(p=.*$/,"")).join("  ");
ansG.appendChild(at); ansG.appendChild(ap); ansG.appendChild(al);
svg.appendChild(ansG);

const rootEl={{}};
const rootDotX = Math.max(150, spineX - 150);
const rootChars = Math.max(18, Math.floor((rootDotX - 24) / 6.2));
words.forEach(w=>{{
  const r=rootByWord[w.i]; if(!r) return;
  const y=wordY(w.i), x0=spineX-26, x1=rootDotX;
  const g=el("g",{{class:"reveal"}}); g.style.cursor="pointer";
  const p=el("path",{{d:`M ${{x0}} ${{y}} C ${{(x0+x1)/2}} ${{y}}, ${{(x0+x1)/2}} ${{y}}, ${{x1}} ${{y}}`,
    fill:"none",stroke:"#ffb547","stroke-width":"1.1","stroke-opacity":"0.5"}}); p.dataset.draw="1";
  g.appendChild(p);
  g.appendChild(el("circle",{{cx:x1,cy:y,r:2.5,fill:"#ffb547"}}));
  const lbl=el("text",{{x:x1-9,y:y+3,"text-anchor":"end",class:"rootlabel","font-size":"10.5"}});
  const txt=(r.label||"");
  lbl.textContent=txt.length>rootChars?txt.slice(0,rootChars-1)+"…":txt;
  g.appendChild(lbl);
  g.addEventListener("mouseenter",()=>{{p.setAttribute("stroke-opacity","1");detail("root · "+w.text,r.full||r.label||"","#ffb547");}});
  g.addEventListener("mouseleave",()=>p.setAttribute("stroke-opacity","0.5"));
  svg.appendChild(g); rootEl[w.i]=g;
}});

const wordEl=[];
words.forEach(w=>{{
  const y=wordY(w.i);
  const g=el("g",{{class:"reveal"}});
  const t=el("text",{{x:spineX,y:y+4,"text-anchor":"middle",class:"wlabel "+w.role,
    "font-size":(w.role==="prompt"?15:11)}});
  t.textContent=w.text.length>24?w.text.slice(0,23)+"…":w.text;
  g.appendChild(t); svg.appendChild(g); wordEl.push(g);
}});

document.getElementById("stage").appendChild(svg);

function drawIn(p){{
  const len=p.getTotalLength?p.getTotalLength():0;
  if(!len){{p.classList.add("in");return;}}
  p.style.transition="none";p.style.strokeDasharray=len;p.style.strokeDashoffset=len;
  p.getBoundingClientRect();p.classList.add("in");
  p.style.transition="stroke-dashoffset .55s ease, opacity .4s ease";p.style.strokeDashoffset="0";
}}
function setStatus(txt,done){{document.getElementById("stxt").innerHTML=txt;if(done)document.getElementById("status").classList.add("done");}}

const PAUSE=1300;
const step1=Math.max(150,Math.min(320,Math.round(2400/nW)));
const ACT1=nW*step1 + PAUSE;
const step2=Math.max(85,Math.min(220,Math.round(2800/maxDepth)));
const ACT2=ACT1 + (maxDepth+1)*step2 + 450 + PAUSE;
const step3=Math.max(110,Math.min(280,Math.round(2600/nW)));

words.forEach(w=>setTimeout(()=>wordEl[w.i].classList.add("in"), w.i*step1));

setTimeout(()=>setStatus("②&nbsp; forward — the attribution graph grows toward the answer…"), ACT1-250);
for(let d=0;d<=maxDepth;d++){{
  setTimeout(()=>{{
    (nodeByDepth[d]||[]).forEach(g=>g.classList.add("in"));
    linkEl.filter(p=>parseInt(p.dataset.tdepth)===d).forEach(drawIn);
  }}, ACT1+d*step2);
}}
setTimeout(()=>ansG.classList.add("in"), ACT1+(maxDepth+1)*step2+200);

setTimeout(()=>setStatus("③&nbsp; backward — the NLA verbalizes what each word means inside the model…"), ACT2-250);
words.forEach(w=>setTimeout(()=>{{
  const g=rootEl[w.i]; if(!g) return;
  g.classList.add("in"); const pp=g.querySelector('path[data-draw]'); if(pp) drawIn(pp);
}}, ACT2+w.i*step3));

setTimeout(()=>{{
  setStatus("the mirror is complete — ① question · ② answer · ③ meaning", true);
  if(NP_URL) document.getElementById("foot").innerHTML=`open the full attribution graph in Neuronpedia ↗`.link(NP_URL);
}}, ACT2+nW*step3+300);
</script>
</body></html>"""


def lens_html(scene: dict) -> str:
    """Vanilla-JS port of LensView.jsx: the optical bench. Scattered prompt → lens
    → converging attribution rays → focal point (the answer) → diverging NLA rays.
    Self-contained — no external scripts beyond Google Fonts."""
    payload = json.dumps(scene)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Fraunces:ital,wght@1,400;1,500&display=swap" rel="stylesheet">
<style>
:root {{ --bg-0:#07090c; --bg-1:#0c1014; --rule:rgba(180,200,230,0.12);
  --ink-0:#e8edf3; --ink-1:#b8c2cf; --ink-2:#8590a0; --ink-3:#5a6473;
  --ctrl:#ffb547; --test:#4ad6c8; --ok:#67e8a4;
  --mono:"JetBrains Mono",monospace; --sans:"Inter Tight",sans-serif; --disp:"Fraunces",serif; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; background:var(--bg-0); color:var(--ink-0); font-family:var(--sans);
  -webkit-font-smoothing:antialiased; }}
.wrap {{ padding:14px 22px; display:flex; flex-direction:column; gap:12px; }}
.head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:24px; flex-wrap:wrap; }}
.kicker {{ font-family:var(--mono); font-size:10.5px; letter-spacing:0.18em;
  text-transform:uppercase; color:var(--ink-2); }}
.title {{ margin:6px 0 0; font-family:var(--disp); font-style:italic; font-weight:400;
  font-size:clamp(20px,2.4vw,30px); line-height:1.12; letter-spacing:-0.02em; max-width:680px; }}
.title .accent {{ font-family:var(--sans); font-style:normal; font-weight:600; }}
.legend {{ display:flex; flex-direction:column; gap:6px; align-items:flex-end; padding-top:4px; }}
.lrow {{ display:flex; align-items:center; gap:8px; font-family:var(--mono); font-size:10.5px;
  letter-spacing:0.10em; text-transform:uppercase; color:var(--ink-1); white-space:nowrap; }}
.sw {{ width:8px; height:8px; border-radius:50%; }}
.stage {{ position:relative; min-height:440px;
  background:radial-gradient(circle at 62% 50%, rgba(74,214,200,0.04), transparent 62%), var(--bg-1);
  border:1px solid var(--rule); border-radius:4px; overflow:hidden; }}
.stage svg {{ position:absolute; inset:0; width:100%; height:100%; }}
.cap {{ font-family:var(--mono); font-size:10.5px; letter-spacing:0.14em; text-transform:uppercase; fill:var(--ink-2); }}
.sub {{ font-family:var(--mono); font-size:10px; letter-spacing:0.12em; text-transform:uppercase; fill:var(--ink-3); }}
.attr {{ font-family:var(--mono); font-size:10.5px; fill:var(--ink-1); letter-spacing:0.01em; }}
.why {{ font-family:var(--disp); font-style:italic; font-size:13px; fill:var(--ink-1); }}
.fock {{ font-family:var(--mono); font-size:10.5px; letter-spacing:0.16em; text-transform:uppercase; }}
.answer {{ position:absolute; left:50%; bottom:18px; transform:translateX(-18%); max-width:340px;
  background:rgba(7,9,12,0.6); backdrop-filter:blur(4px); border:1px solid var(--rule);
  border-left:2px solid var(--ok); border-radius:3px; padding:10px 14px;
  transition:opacity .6s ease; opacity:0; }}
.answer p {{ margin:5px 0 0; font-family:var(--disp); font-style:italic; font-size:15px;
  line-height:1.4; color:var(--ink-0); text-wrap:pretty; }}
.foot {{ display:flex; align-items:center; justify-content:space-between; gap:20px; flex-wrap:wrap;
  padding:12px 16px; background:var(--bg-1); border:1px solid var(--rule); border-radius:4px; }}
.status {{ display:flex; align-items:center; gap:10px; font-family:var(--mono); font-size:11.5px;
  color:var(--ink-2); line-height:1.4; }}
.status b {{ color:var(--ink-0); font-weight:500; }}
.dot {{ width:8px; height:8px; border-radius:50%; box-shadow:0 0 8px currentColor;
  animation:pulse 1.4s ease-in-out infinite; background:var(--ink-3); color:var(--ink-3); }}
.status.done .dot {{ animation:none; background:var(--ok); color:var(--ok); }}
@keyframes pulse {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.35;}} }}
.phases {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.chip {{ display:flex; align-items:center; gap:6px; padding:4px 9px; border-radius:3px;
  border:1px solid var(--rule); opacity:0.4; transition:all .3s; }}
.chip.on {{ opacity:1; }}
.chip.cur {{ background:#161c24; }}
.chip .k {{ font-family:var(--mono); font-size:9px; color:var(--ink-3); letter-spacing:0.08em; }}
.chip.on .k {{ color:var(--test); }}
.chip .t {{ font-family:var(--mono); font-size:10px; letter-spacing:0.10em;
  text-transform:uppercase; color:var(--ink-1); }}
@media (max-width: 1100px) {{
  .answer {{ left:12px; right:auto; bottom:12px; transform:none;
    max-width:min(46%, 320px); }}
  .legend {{ align-items:flex-start; }}
  .stage {{ min-height:380px; }}
}}
.replay {{ font-family:var(--mono); font-size:10px; letter-spacing:0.12em; text-transform:uppercase;
  padding:3px 10px; border:1px solid var(--rule); background:transparent; color:var(--ink-2);
  border-radius:3px; cursor:pointer; margin-left:6px; }}
.replay:hover {{ color:var(--ink-0); border-color:rgba(180,200,230,0.32); }}
.reveal {{ opacity:0; }}
.reveal.in {{ opacity:1; transition:opacity .5s ease; }}
</style></head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <div class="kicker">Focal lines · the lens</div>
      <div class="title">Where the knowledge layer <span class="accent">bends the light</span></div>
    </div>
    <div class="legend">
      <span class="lrow"><span class="sw" style="background:#4ad6c8"></span>Converge · attribution</span>
      <span class="lrow"><span class="sw" style="background:#67e8a4"></span>Focal point · answer</span>
      <span class="lrow"><span class="sw" style="background:#ffb547"></span>Diverge · NLA mirror</span>
    </div>
  </div>
  <div class="stage" id="stage"></div>
  <div class="foot">
    <div class="status" id="status"><span class="dot" id="dot"></span><span id="stxt">Standing by…</span></div>
    <div class="phases" id="phases"></div>
  </div>
</div>
<script>
const S = {payload};
const NS = "http://www.w3.org/2000/svg";
const VB_W=1200, VB_H=700, SRC_X=96, LENS_X=350, FOC_X=822, FOC_Y=350, END_X=1140;
const TEST="#4ad6c8", CTRL="#ffb547", OK="#67e8a4";
const PHASES = [
  {{k:"01", t:"The throw", d:"the prompt enters, semantically scattered"}},
  {{k:"02", t:"Converge", d:"the lens focuses the rays — each marks a knowledge object"}},
  {{k:"03", t:"Focal point", d:"the rays cross. the answer."}},
  {{k:"04", t:"Diverge", d:"the semantic mirror voices why each ray landed"}},
];

function el(tag, attrs){{ const e=document.createElementNS(NS, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]); return e; }}
function len(x1,y1,x2,y2){{ return Math.hypot(x2-x1, y2-y1); }}

function buildStage(){{
  const stage = document.getElementById("stage");
  stage.innerHTML = "";
  const svg = el("svg", {{viewBox:`0 0 ${{VB_W}} ${{VB_H}}`, preserveAspectRatio:"xMidYMid meet"}});
  const defs = el("defs", {{}});
  defs.innerHTML = `
    <radialGradient id="focGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="${{OK}}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="${{OK}}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="lensFill" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="${{TEST}}" stop-opacity="0.04"/>
      <stop offset="50%" stop-color="${{TEST}}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="${{TEST}}" stop-opacity="0.04"/>
    </linearGradient>`;
  svg.appendChild(defs);

  svg.appendChild(el("line", {{x1:SRC_X, y1:FOC_Y, x2:END_X, y2:FOC_Y,
    stroke:"rgba(180,200,230,0.16)", "stroke-width":"1", "stroke-dasharray":"2 6"}}));

  const cap1 = el("text", {{x:SRC_X-8, y:36, class:"cap reveal", "data-phase":"1"}}); cap1.textContent="① SCATTERED PROMPT"; svg.appendChild(cap1);
  const cap2 = el("text", {{x:(LENS_X+FOC_X)/2, y:36, "text-anchor":"middle", class:"cap reveal", "data-phase":"2", fill:TEST}});
  cap2.textContent="② CONVERGE · ATTRIBUTION GRAPH"; svg.appendChild(cap2);
  const cap4 = el("text", {{x:(FOC_X+END_X)/2+20, y:36, "text-anchor":"middle", class:"cap reveal", "data-phase":"4", fill:CTRL}});
  cap4.textContent="④ DIVERGE · NLA SEMANTIC MIRROR"; svg.appendChild(cap4);

  const rays = (S.rays||[]).map((r,i)=>({{...r, i,
    enterL: len(SRC_X, r.sy, LENS_X, r.ly),
    convL: len(LENS_X, r.ly, FOC_X, FOC_Y),
    divL: len(FOC_X, FOC_Y, END_X, r.dy),
    ax: (LENS_X+FOC_X)/2, ay:(r.ly+FOC_Y)/2,
    nx: FOC_X + 0.5*(END_X-FOC_X), ny: FOC_Y + 0.5*(r.dy-FOC_Y),
    fullPath: `M ${{SRC_X}} ${{r.sy}} L ${{LENS_X}} ${{r.ly}} L ${{FOC_X}} ${{FOC_Y}} L ${{END_X}} ${{r.dy}}`
  }}));

  function dashLine(x1,y1,x2,y2,stroke,sw,L,phase,delay){{
    const ln = el("line",{{x1,y1,x2,y2, stroke, "stroke-width":sw,
      "stroke-dasharray":L, "stroke-dashoffset":L}});
    ln.dataset.phase = phase; ln.dataset.delay = delay; ln.dataset.len = L;
    svg.appendChild(ln); return ln;
  }}

  rays.forEach(r => dashLine(SRC_X, r.sy, LENS_X, r.ly, "rgba(180,200,230,0.45)", 1, r.enterL, 1, r.i*60));
  rays.forEach(r => {{
    const g = el("g", {{class:"reveal", "data-phase":"1", "data-delay":r.i*60}});
    g.appendChild(el("circle", {{cx:SRC_X, cy:r.sy, r:3.5, fill:"rgba(184,194,207,0.9)"}}));
    svg.appendChild(g);
  }});
  const slbl = el("text", {{x:SRC_X-4, y:VB_H-24, class:"sub reveal", "data-phase":"1", "data-delay":100}});
  slbl.textContent = S.source_label||""; svg.appendChild(slbl);

  const lensG = el("g", {{class:"reveal", "data-phase":"1", "data-delay":250}});
  lensG.appendChild(el("path", {{d:`M ${{LENS_X}} 150 C ${{LENS_X+30}} 230, ${{LENS_X+30}} 470, ${{LENS_X}} 550 C ${{LENS_X-30}} 470, ${{LENS_X-30}} 230, ${{LENS_X}} 150 Z`,
    fill:"url(#lensFill)", stroke:TEST, "stroke-opacity":"0.55", "stroke-width":"1.2"}}));
  lensG.appendChild(el("line", {{x1:LENS_X, y1:150, x2:LENS_X, y2:550, stroke:TEST,
    "stroke-opacity":"0.3", "stroke-width":"0.6", "stroke-dasharray":"2 4"}}));
  const llbl = el("text", {{x:LENS_X, y:596, "text-anchor":"middle", class:"sub", fill:TEST}});
  llbl.textContent = S.lens_label||""; lensG.appendChild(llbl);
  svg.appendChild(lensG);

  rays.forEach(r => dashLine(LENS_X, r.ly, FOC_X, FOC_Y, TEST, 1.3, r.convL, 2, r.i*120));
  rays.forEach(r => {{
    const g = el("g", {{class:"reveal", "data-phase":"2", "data-delay":r.i*120 + 400}});
    g.appendChild(el("circle", {{cx:r.ax, cy:r.ay, r:5, fill:"#0c1014", stroke:TEST, "stroke-width":"1.4"}}));
    g.appendChild(el("circle", {{cx:r.ax, cy:r.ay, r:1.8, fill:TEST}}));
    const t = el("text", {{x:r.ax, y:r.ay-12, "text-anchor":"middle", class:"attr"}});
    t.textContent = r.attr||""; g.appendChild(t);
    svg.appendChild(g);
  }});

  const focG = el("g", {{class:"reveal", "data-phase":"3", "data-delay":0}});
  const glow = el("circle", {{cx:FOC_X, cy:FOC_Y, r:64, fill:"url(#focGlow)"}});
  const anim = el("animate", {{attributeName:"r", values:"48;66;48", dur:"3.2s", repeatCount:"indefinite"}});
  glow.appendChild(anim); focG.appendChild(glow);
  focG.appendChild(el("circle", {{cx:FOC_X, cy:FOC_Y, r:22, fill:"none", stroke:OK, "stroke-opacity":"0.4", "stroke-width":"0.8", "stroke-dasharray":"3 4"}}));
  focG.appendChild(el("circle", {{cx:FOC_X, cy:FOC_Y, r:11, fill:"none", stroke:OK, "stroke-opacity":"0.6", "stroke-width":"0.8"}}));
  focG.appendChild(el("circle", {{cx:FOC_X, cy:FOC_Y, r:4, fill:OK}}));
  const fk = el("text", {{x:FOC_X, y:FOC_Y-78, "text-anchor":"middle", class:"fock", fill:OK}});
  fk.textContent = "③ FOCAL POINT · THE ANSWER"; focG.appendChild(fk);
  svg.appendChild(focG);

  rays.forEach(r => dashLine(FOC_X, FOC_Y, END_X, r.dy, CTRL, 1.2, r.divL, 4, r.i*100));
  rays.forEach(r => {{
    const g = el("g", {{class:"reveal", "data-phase":"4", "data-delay":r.i*100 + 350}});
    g.appendChild(el("circle", {{cx:END_X, cy:r.dy, r:3, fill:CTRL}}));
    const t = el("text", {{x:END_X-10, y:r.dy+3, "text-anchor":"end", class:"why"}});
    t.textContent = r.why||""; g.appendChild(t);
    svg.appendChild(g);
  }});

  stage.appendChild(svg);

  const ans = document.createElement("div");
  ans.className = "answer"; ans.id = "answer";
  ans.innerHTML = `<span class="kicker" style="color:${{OK}}">resolved answer</span><p>${{(S.answer||"").replace(/</g,"&lt;")}}</p>`;
  stage.appendChild(ans);

  return {{svg, rays}};
}}

function buildPhases(){{
  const wrap = document.getElementById("phases");
  wrap.innerHTML = "";
  PHASES.forEach((p, i) => {{
    const c = document.createElement("div"); c.className = "chip"; c.id = `chip-${{i+1}}`;
    c.innerHTML = `<span class="k">${{p.k}}</span><span class="t">${{p.t}}</span>`;
    wrap.appendChild(c);
  }});
  const btn = document.createElement("button"); btn.className = "replay"; btn.textContent = "↻ Replay";
  btn.onclick = run; wrap.appendChild(btn);
}}

function setStatus(html, done){{
  document.getElementById("stxt").innerHTML = html;
  const s = document.getElementById("status");
  if(done) s.classList.add("done"); else s.classList.remove("done");
  const dot = document.getElementById("dot");
  dot.style.color = done ? OK : TEST;
}}

function applyPhase(phase){{
  document.querySelectorAll("[data-phase]").forEach(el => {{
    const ep = parseInt(el.dataset.phase || "0");
    const delay = parseInt(el.dataset.delay || "0");
    if(ep <= phase){{
      setTimeout(() => {{
        el.classList.add("in");
        if(el.tagName === "line" && el.dataset.len){{
          const L = el.dataset.len;
          el.style.transition = `stroke-dashoffset 0.75s cubic-bezier(.55,0,.25,1)`;
          el.style.strokeDashoffset = "0";
          el.style.opacity = "1";
        }}
      }}, delay);
    }}
  }});
  for(let i=1; i<=4; i++){{
    const c = document.getElementById(`chip-${{i}}`);
    if(!c) continue;
    c.classList.toggle("on", phase >= i);
    c.classList.toggle("cur", phase === i);
  }}
  document.getElementById("answer").style.opacity = phase >= 3 ? 1 : 0;
  if(phase === 0) setStatus("Standing by…", false);
  else if(phase >= 5) setStatus("<b>The focal line, resolved</b> · converge → cross → diverge. Attribution and NLA are two halves of one ray path.", true);
  else {{ const p = PHASES[phase-1]; setStatus(`<b>${{p.k}} · ${{p.t}}</b> — ${{p.d}}`, false); }}
}}

let timers = [];
function run(){{
  timers.forEach(clearTimeout); timers = [];
  buildStage(); buildPhases(); applyPhase(0);
  const at = (ms, p) => timers.push(setTimeout(() => applyPhase(p), ms));
  at(350, 1); at(2300, 2); at(5400, 3); at(7000, 4); at(10600, 5);
}}
run();
</script></body></html>"""


def _lens_height() -> int:
    """Fixed-aspect stage: viewBox is 1200x700; account for head + foot chrome."""
    return 760


def _scene_height(scene) -> int:
    """Approximate the iframe height from word count (the SVG scales to container width)."""
    n = max(scene.get("meta", {}).get("word_count", 1), 1)
    row = max(30, min(72, 820 // n))
    svg_h = 108 + (n - 1) * row
    return min(1300, max(480, int(0.62 * svg_h) + 220))


def combined_graph_html(compiled_graph: dict) -> str:
    """Progressive disclosure viz for a compiled attribution graph (borges_graph JSON).

    Layout: X = depth (0..max_depth), Y = ctx_idx (0..max_ctx).
    Step slider reveals one autoregressive step at a time.
    Nodes coloured by type; size ∝ influence. Hover shows detail.
    """
    import json as _json
    data_js = _json.dumps(compiled_graph)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0f; color: #c8c8d8; font-family: 'SF Mono', 'Fira Code', monospace;
         font-size: 12px; overflow: hidden; }}
  #wrap {{ display: flex; flex-direction: column; height: 100vh; padding: 12px 16px 8px; gap: 8px; }}
  #header {{ display:flex; align-items:baseline; gap:12px; flex-shrink:0; }}
  #header h1 {{ font-size:13px; font-weight:600; color:#e0e0f0; letter-spacing:.06em; }}
  #header .prompt {{ color:#7878a0; font-size:11px; }}
  #controls {{ display:flex; align-items:center; gap:16px; flex-shrink:0; }}
  #step-label {{ color:#a0a0c0; font-size:11px; min-width:220px; }}
  #step-slider {{ flex:1; accent-color:#7c6ff7; cursor:pointer; }}
  #playBtn {{ background:#1e1e2e; border:1px solid #3a3a5a; color:#c8c8d8;
              padding:3px 10px; border-radius:4px; cursor:pointer; font-size:11px; }}
  #playBtn:hover {{ background:#2a2a3e; }}
  #cumul-toggle {{ display:flex; align-items:center; gap:6px; color:#a0a0c0; font-size:11px; cursor:pointer; }}
  #main-row {{ display:flex; flex:1; gap:12px; min-height:0; }}
  #canvas-wrap {{ flex:1; position:relative; min-height:0; }}
  canvas {{ position:absolute; inset:0; width:100%; height:100%; }}
  #contrib-panel {{ width:200px; flex-shrink:0; display:flex; flex-direction:column; gap:6px;
                    border-left:1px solid #1e1e2e; padding-left:12px; }}
  #contrib-title {{ font-size:10px; color:#606080; letter-spacing:.05em; text-transform:uppercase; flex-shrink:0; }}
  #contrib-target {{ font-size:11px; color:#e0a050; font-weight:600; flex-shrink:0; }}
  #contrib-bars {{ flex:1; display:flex; flex-direction:column; justify-content:center; gap:5px; }}
  .cb-row {{ display:flex; flex-direction:column; gap:2px; }}
  .cb-label {{ display:flex; justify-content:space-between; font-size:10px; color:#a0a0c0; }}
  .cb-label .cb-tok {{ color:#c8c8d8; max-width:110px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .cb-label .cb-pct {{ color:#7c6ff7; font-weight:600; flex-shrink:0; }}
  .cb-track {{ height:5px; background:#1a1a2e; border-radius:3px; overflow:hidden; }}
  .cb-fill {{ height:100%; border-radius:3px; transition:width .35s ease; }}
  #tooltip {{ position:fixed; background:#1a1a2e; border:1px solid #3a3a5a; border-radius:6px;
              padding:8px 10px; pointer-events:none; display:none; z-index:10;
              line-height:1.6; max-width:260px; }}
  #tooltip .tid  {{ color:#7c6ff7; font-weight:600; }}
  #tooltip .tlabel {{ color:#7fbe8a; font-style:italic; margin-top:2px; }}
  #legend {{ display:flex; gap:14px; flex-shrink:0; align-items:center; padding-bottom:2px; }}
  .leg {{ display:flex; align-items:center; gap:5px; color:#8080a0; font-size:10px; }}
  .leg-dot {{ width:9px; height:9px; border-radius:50%; flex-shrink:0; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="header">
    <h1>ATTRIBUTION GRAPH</h1>
    <span class="prompt" id="prompt-txt"></span>
  </div>
  <div id="controls">
    <button id="playBtn">▶ Play</button>
    <input type="range" id="step-slider" min="0" step="1" value="0">
    <span id="step-label">—</span>
    <label id="cumul-toggle">
      <input type="checkbox" id="cumul-cb" checked> accumulate steps
    </label>
  </div>
  <div id="main-row">
    <div id="canvas-wrap">
      <canvas id="bg"></canvas>
      <canvas id="fg"></canvas>
    </div>
    <div id="contrib-panel">
      <div id="contrib-title">logit contribution</div>
      <div id="contrib-target">—</div>
      <div id="contrib-bars"></div>
    </div>
  </div>
  <div id="legend">
    <span class="leg"><span class="leg-dot" style="background:#4a6fa5"></span>embedding</span>
    <span class="leg"><span class="leg-dot" style="background:#7c6ff7"></span>transcoder</span>
    <span class="leg"><span class="leg-dot" style="background:#e0a050"></span>logit</span>
    <span class="leg" style="margin-left:8px; color:#606080">size ∝ influence · opacity ∝ link weight</span>
  </div>
</div>
<div id="tooltip"></div>

<script>
(function(){{
  const RAW = {data_js};

  // ── palette ──────────────────────────────────────────────────────────────
  const COL = {{
    embedding: "#4a6fa5",
    "cross layer transcoder": "#7c6ff7",
    logit: "#e0a050",
  }};
  const STEPS = RAW.steps;
  const MAX_STEP = STEPS.length - 1;

  // ── build global node/link index ─────────────────────────────────────────
  // Each node gets a step_index (first step it appears in)
  const nodeMap = {{}};   // id -> {{...node, stepIdx}}
  const linksByStep = []; // array[stepIdx] = [{{source,target,weight}}]

  STEPS.forEach((s, si) => {{
    s.subgraph.nodes.forEach(n => {{
      if (!nodeMap[n.id]) nodeMap[n.id] = {{ ...n, stepIdx: si }};
    }});
    linksByStep.push(s.subgraph.links || []);
  }});

  const allNodes = Object.values(nodeMap);

  // ── cluster pre-computation ───────────────────────────────────────────────
  // clustersByStep[si] = Map<"depth:ctx_idx" -> {{depth, ctx_idx, count, totalInf, type, topLabel}}>
  // clusterLinksbyStep[si] = [{{srcKey, tgtKey, totalWeight}}]
  const clustersByStep = STEPS.map((s, si) => {{
    const map = new Map();
    s.subgraph.nodes.forEach(n => {{
      const key = `${{n.depth}}:${{n.ctx_idx}}`;
      if (!map.has(key)) map.set(key, {{
        depth: n.depth, ctx_idx: n.ctx_idx, count: 0, totalInf: 0,
        type: n.type, topLabel: "", topInf: -1,
      }});
      const c = map.get(key);
      c.count++;
      c.totalInf += Math.abs(n.influence);
      if (Math.abs(n.influence) > c.topInf) {{
        c.topInf = Math.abs(n.influence);
        c.topLabel = n.label || "";
      }}
    }});
    return map;
  }});

  // aggregate links into cluster-to-cluster weights
  const clusterLinksByStep = STEPS.map((s, si) => {{
    const agg = new Map(); // "srcKey->tgtKey" -> totalWeight
    const nodeToKey = {{}};
    s.subgraph.nodes.forEach(n => {{ nodeToKey[n.id] = `${{n.depth}}:${{n.ctx_idx}}`; }});
    (s.subgraph.links || []).forEach(l => {{
      const sk = nodeToKey[l.source], tk = nodeToKey[l.target];
      if (!sk || !tk || sk === tk) return;
      const key = sk + "|" + tk;
      agg.set(key, (agg.get(key) || 0) + Math.abs(l.weight));
    }});
    // convert to array, sorted desc by weight
    return Array.from(agg.entries())
      .map(([k, w]) => {{ const [sk, tk] = k.split("|"); return {{sk, tk, w}}; }})
      .sort((a, b) => b.w - a.w)
      .slice(0, 800); // top 800 cluster-links per step
  }});

  // ── layout grid ──────────────────────────────────────────────────────────
  const maxDepth = Math.max(...allNodes.map(n => n.depth));
  const maxCtx   = Math.max(...allNodes.map(n => n.ctx_idx));

  function clusterXY(depth, ctx_idx) {{
    const PAD_L = 80, PAD_R = 120, PAD_T = 36, PAD_B = 36;
    const x = PAD_L + (depth   / maxDepth)       * (W - PAD_L - PAD_R);
    const y = PAD_T + (ctx_idx / Math.max(maxCtx,1)) * (H - PAD_T - PAD_B);
    return [x, y];
  }}

  function toXY(node, W, H) {{
    return clusterXY(node.depth, node.ctx_idx);
  }}

  // ── canvas setup ─────────────────────────────────────────────────────────
  const bgC  = document.getElementById("bg");
  const fgC  = document.getElementById("fg");
  const bgCtx = bgC.getContext("2d");
  const fgCtx = fgC.getContext("2d");
  let W = 0, H = 0, DPR = window.devicePixelRatio || 1;

  function resize() {{
    const wrap = document.getElementById("canvas-wrap");
    W = wrap.clientWidth; H = wrap.clientHeight;
    [bgC, fgC].forEach(c => {{
      c.width  = W * DPR; c.height = H * DPR;
      c.style.width  = W + "px"; c.style.height = H + "px";
    }});
    bgCtx.scale(DPR, DPR); fgCtx.scale(DPR, DPR);
    drawGrid();
    render();
  }}
  new ResizeObserver(resize).observe(document.getElementById("canvas-wrap"));

  // ── grid (bg canvas) ─────────────────────────────────────────────────────
  function drawGrid() {{
    bgCtx.clearRect(0,0,W,H);
    bgCtx.strokeStyle = "#1c1c2c";
    bgCtx.lineWidth = 0.5;
    const PAD_L = 80, PAD_R = 120, PAD_T = 36, PAD_B = 36;
    for (let d = 0; d <= maxDepth; d += 5) {{
      const x = PAD_L + (d / maxDepth) * (W - PAD_L - PAD_R);
      bgCtx.beginPath(); bgCtx.moveTo(x, PAD_T); bgCtx.lineTo(x, H-PAD_B);
      bgCtx.stroke();
      bgCtx.fillStyle = "#404060"; bgCtx.font = "9px monospace";
      bgCtx.fillText("L" + d, x-8, PAD_T-6);
    }}
    for (let c = 0; c <= maxCtx; c++) {{
      const y = PAD_T + (c / Math.max(maxCtx,1)) * (H - PAD_T - PAD_B);
      bgCtx.beginPath(); bgCtx.moveTo(PAD_L, y); bgCtx.lineTo(W-PAD_R, y);
      bgCtx.stroke();
    }}
  }}

  // ── main render ──────────────────────────────────────────────────────────
  let currentStep = 0;
  let cumulative = true;

  function visibleUpTo(step) {{
    return cumulative ? step : step; // filter differs below
  }}

  function render() {{
    if (!W || !H) return;
    fgCtx.clearRect(0,0,W,H);

    const step = currentStep;

    // ── cluster links (batched by alpha bucket) ──────────────────────────────
    const ALPHA_BUCKETS = 6;
    for (let si = 0; si <= step; si++) {{
      if (!cumulative && si < step) continue;
      const clinks = clusterLinksByStep[si];
      if (!clinks.length) continue;
      const maxW = clinks[0].w;
      const isCurrentStep = (si === step);

      const buckets = Array.from({{length: ALPHA_BUCKETS}}, () => []);
      clinks.forEach(cl => {{
        const [x1,y1] = clusterXY(...cl.sk.split(":").map(Number));
        const [x2,y2] = clusterXY(...cl.tk.split(":").map(Number));
        const bucket = Math.min(ALPHA_BUCKETS-1, Math.floor((cl.w/maxW) * ALPHA_BUCKETS));
        buckets[bucket].push([x1,y1,x2,y2]);
      }});

      fgCtx.lineWidth = isCurrentStep ? 1.0 : 0.5;
      buckets.forEach((segs, bi) => {{
        if (!segs.length) return;
        const baseAlpha = 0.04 + (bi / ALPHA_BUCKETS) * 0.32;
        const alpha = isCurrentStep ? baseAlpha : baseAlpha * 0.4;
        fgCtx.strokeStyle = `rgba(120,110,200,${{alpha.toFixed(3)}})`;
        fgCtx.beginPath();
        segs.forEach(([x1,y1,x2,y2]) => {{ fgCtx.moveTo(x1,y1); fgCtx.lineTo(x2,y2); }});
        fgCtx.stroke();
      }});
    }}

    // ── cluster dots ─────────────────────────────────────────────────────────
    // collect all visible clusters; normalise radius across all visible steps
    let allVisible = [];
    for (let si = 0; si <= step; si++) {{
      if (!cumulative && si < step) continue;
      clustersByStep[si].forEach((c, key) => {{
        allVisible.push({{...c, stepIdx: si, key}});
      }});
    }}
    const maxInf = Math.max(...allVisible.map(c => c.totalInf), 1);

    allVisible.forEach(c => {{
      const [x, y] = clusterXY(c.depth, c.ctx_idx);
      const r = 4 + (c.totalInf / maxInf) * 22;
      const isNew = (c.stepIdx === step);
      const col = COL[c.type] || "#808080";

      fgCtx.globalAlpha = isNew ? 1.0 : 0.35;
      fgCtx.beginPath();
      fgCtx.arc(x, y, r, 0, Math.PI*2);
      fgCtx.fillStyle = col;
      fgCtx.fill();

      // ring on current step clusters
      if (isNew) {{
        fgCtx.strokeStyle = "rgba(255,255,255,0.25)";
        fgCtx.lineWidth = 1;
        fgCtx.stroke();
      }}

      // node count badge
      fgCtx.globalAlpha = isNew ? 0.9 : 0.4;
      fgCtx.font = `${{Math.max(8, Math.min(11, r))}}px monospace`;
      fgCtx.fillStyle = "#ffffff";
      fgCtx.textAlign = "center";
      fgCtx.textBaseline = "middle";
      fgCtx.fillText(c.count, x, y);
      fgCtx.textAlign = "left";
      fgCtx.textBaseline = "alphabetic";

      // top label for logit clusters
      if (c.topLabel && c.depth >= maxDepth - 2) {{
        fgCtx.globalAlpha = isNew ? 0.95 : 0.4;
        fgCtx.font = "9px monospace";
        fgCtx.fillStyle = "#e8d080";
        fgCtx.fillText(c.topLabel.replace("Output ","").slice(0,18), x + r + 4, y + 3);
      }}
      fgCtx.globalAlpha = 1;
    }});

    // Step token badge top-right
    const tok = STEPS[step].token;
    fgCtx.font = "bold 14px monospace";
    fgCtx.fillStyle = "#7c6ff7";
    fgCtx.fillText(`→ "${{tok.trim()}}"`, W - 140, 22);
    fgCtx.font = "10px monospace";
    fgCtx.fillStyle = "#606080";
    fgCtx.fillText(`step ${{step+1}}/${{STEPS.length}}`, W - 140, 36);
  }}

  // ── tooltip on hover ─────────────────────────────────────────────────────
  const tip = document.getElementById("tooltip");

  fgC.addEventListener("mousemove", e => {{
    if (!W || !H) return;
    const rect = fgC.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let hit = null, bestD = 28;

    for (let si = 0; si <= currentStep; si++) {{
      if (!cumulative && si < currentStep) continue;
      clustersByStep[si].forEach((c, key) => {{
        const [x,y] = clusterXY(c.depth, c.ctx_idx);
        const d = Math.hypot(mx-x, my-y);
        if (d < bestD) {{ bestD = d; hit = {{...c, stepIdx: si}}; }}
      }});
    }}

    if (hit) {{
      const lines = [
        `<span class="tid">layer ${{hit.depth - 1}} · ctx ${{hit.ctx_idx}}</span>`,
        `nodes: <b>${{hit.count}}</b>`,
        `total influence: <b>${{hit.totalInf.toFixed(3)}}</b>`,
        `mean per node: ${{(hit.totalInf / hit.count).toFixed(3)}}`,
        `step introduced: ${{hit.stepIdx + 1}}`,
      ];
      if (hit.topLabel) lines.push(`<span class="tlabel">top: ${{hit.topLabel}}</span>`);
      tip.innerHTML = lines.join("<br>");
      tip.style.display = "block";
      tip.style.left = (e.clientX + 14) + "px";
      tip.style.top  = (e.clientY - 10) + "px";
    }} else {{
      tip.style.display = "none";
    }}
  }});
  fgC.addEventListener("mouseleave", () => {{ tip.style.display = "none"; }});

  // ── contribution panel ───────────────────────────────────────────────────
  const CONTRIBS = RAW.logit_contributions || [];

  // token-position colour: same hue family as the graph, varied by position
  const CTX_COLORS = ["#4a6fa5","#7c6ff7","#e0a050","#5fbeaa","#c05f7a","#8fc05f","#c09f5f","#7f9fc0","#bf7fc0"];

  function updateContrib() {{
    const contrib = CONTRIBS[currentStep];
    const tok = STEPS[currentStep].token;
    document.getElementById("contrib-target").textContent = `→ "${{tok.trim()}}"`;
    const container = document.getElementById("contrib-bars");
    container.innerHTML = "";
    if (!contrib) return;
    contrib.forEach(row => {{
      const color = CTX_COLORS[row.ctx_idx % CTX_COLORS.length];
      const div = document.createElement("div");
      div.className = "cb-row";
      div.innerHTML = `
        <div class="cb-label">
          <span class="cb-tok">${{row.token}}</span>
          <span class="cb-pct">${{row.share}}%</span>
        </div>
        <div class="cb-track">
          <div class="cb-fill" style="width:${{row.share}}%;background:${{color}}"></div>
        </div>`;
      container.appendChild(div);
    }});
  }}

  // ── slider & controls ────────────────────────────────────────────────────
  const slider = document.getElementById("step-slider");
  slider.max = MAX_STEP;

  function updateLabel() {{
    const tok = STEPS[currentStep].token;
    const ctx = STEPS[currentStep].context_length;
    const nn  = STEPS[currentStep].subgraph.nodes.length;
    const nl  = STEPS[currentStep].subgraph.links.length;
    document.getElementById("step-label").textContent =
      `step ${{currentStep+1}}: "${{tok.trim()}}" · ctx=${{ctx}} · ${{nn}} nodes · ${{nl}} links`;
    updateContrib();
  }}

  slider.addEventListener("input", () => {{
    currentStep = +slider.value;
    updateLabel(); render();
  }});

  document.getElementById("cumul-cb").addEventListener("change", e => {{
    cumulative = e.target.checked; render();
  }});

  // auto-play
  let playTimer = null;
  document.getElementById("playBtn").addEventListener("click", function() {{
    if (playTimer) {{
      clearInterval(playTimer); playTimer = null;
      this.textContent = "▶ Play";
    }} else {{
      this.textContent = "⏸ Pause";
      playTimer = setInterval(() => {{
        currentStep = (currentStep + 1) % (MAX_STEP + 1);
        slider.value = currentStep;
        updateLabel(); render();
      }}, 1200);
    }}
  }});

  document.getElementById("prompt-txt").textContent =
    `"${{RAW.prompt}}" → "${{RAW.generated_text.trim()}}"`;

  updateLabel();
}})();
</script>
</body>
</html>"""

