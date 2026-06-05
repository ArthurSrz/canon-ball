"""
Canon Ball — Landing page
Navigate to Canon Ball (experiment) or Borges Graph (attribution) via the sidebar.
"""

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="Canon Ball", page_icon="🎯", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("<style>footer { display: none !important; }</style>", unsafe_allow_html=True)

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
.nav { margin-top:32px; display:flex; gap:24px; justify-content:center; }
.nav a { color:#4ad6c8; text-decoration:none; font-family:"JetBrains Mono",monospace;
  font-size:12px; letter-spacing:0.12em; text-transform:uppercase;
  padding:8px 18px; border:1px solid rgba(74,214,200,0.35); border-radius:4px; }
.nav a:hover { background:rgba(74,214,200,0.08); border-color:rgba(74,214,200,0.6); }
</style>
</head><body>
<div>
  <svg class="mark" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="18" stroke="#4ad6c8" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
    <circle cx="24" cy="24" r="10" stroke="#ffb547" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
    <circle cx="24" cy="24" r="3" fill="#4ad6c8"/>
  </svg>
  <h1>Canon Ball</h1>
  <p>Measuring holism: where does the ball land<br/>
  with and without a knowledge layer?</p>
  <p style="margin-top:24px; color:#5a6473;">
  Use the sidebar to navigate between instruments.
  </p>
</div>
</body></html>""", height=500, scrolling=False)
