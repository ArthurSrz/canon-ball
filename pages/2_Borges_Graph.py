"""
Borges Graph — Compiled Attribution Graph page
Builds an autoregressive chain of attribution graphs: each step generates a token,
records the causal graph that produced it, then appends the token to the context.
"""

import streamlit as st
import streamlit.components.v1 as components

import neuronpedia_client as npc
from shared_sidebar import render_shared_sidebar
from html_components import lens_html, mise_en_abime_html, _lens_height, _scene_height


st.set_page_config(page_title="Borges Graph", page_icon="🪞", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("<style>footer { display: none !important; }</style>", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    shared = render_shared_sidebar()
    prompt = shared["prompt"]
    knowledge_layer = shared["knowledge_layer"]

    st.divider()
    st.caption("🪞 BORGES GRAPH")

    nla_model = st.selectbox(
        "Model · the brain",
        options=["gemma-3-27b-it", "llama3.3-70b-it"],
        format_func=lambda m: {"gemma-3-27b-it": "Gemma 3 27B (layer 41)",
                               "llama3.3-70b-it": "Llama 3.3 70B (layer 53)"}[m],
    )
    nla_source = {"gemma-3-27b-it": "kitft-l41", "llama3.3-70b-it": "kitft-l53"}[nla_model]
    nla_max_tokens = st.slider("Max tokens to verbalize", 16, 256, 128, step=16,
                               help="Verbalizes EVERY token up to this cap (system prompt + prompt), "
                                    "batched 16/request. Higher = more API calls = slower.")
    nla_include_system = st.checkbox("Include knowledge layer as context", value=True,
                                     help="Prepend the knowledge layer to the prompt so its tokens "
                                          "are verbalized too.")
    trace_attrib = st.checkbox("Also trace attribution circuit (Circuit Tracer)", value=True,
                               help="Generate the real causal attribution graph (gemma-2-2b) showing "
                                    "how the answer is formed — feature nodes + attribution edges to the "
                                    "output logits. Uses the prompt only (64-token cap).")
    mirror_style = st.radio(
        "Mirror style",
        options=["Lens (focal lines)", "Mise-en-abîme (raw)"],
        index=0, horizontal=False, key="mirror_style",
        help="Lens: the optical-bench view — converge → focal point → diverge. "
             "Mise-en-abîme: the full token spine with every NLA root + the pruned attribution tree.",
    )
    mirror_btn = st.button("Reveal internal features", use_container_width=True)


# --- Scene computation (moved from app.py) ---

def compute_scene(prompt, knowledge, nla_result, do_trace):
    """Generate the attribution graph (best-effort), prune it, and assemble the unified scene."""
    attrib_meta = npc.generate_attribution_graph(prompt) if do_trace else None
    subgraph, np_url = None, ""
    if attrib_meta and attrib_meta.get("ok"):
        np_url = attrib_meta.get("url", "")
        subgraph = npc.fetch_attribution_subgraph(attrib_meta["s3url"], max_nodes=24, max_links=120)
    scene = npc.build_mise_en_abime_scene(prompt, knowledge, nla_result, subgraph)
    return scene, np_url, attrib_meta


def render_scene(scene, np_url, attrib_status, answer=""):
    """Render the unified scene, with graceful degradation for failed components."""
    if attrib_status and not attrib_status.get("ok"):
        if attrib_status.get("busy"):
            st.warning(f"Attribution circuit unavailable (GPUs busy) — roots only. "
                       f"({attrib_status.get('error','')})")
        else:
            st.caption(f"Attribution circuit unavailable: {attrib_status.get('error','')}")
    if not scene["meta"].get("nla_ok") and not npc._np_key():
        st.info("Tip: set `NEURONPEDIA_API_KEY` to raise rate limits "
                "(the NLA API also works key-less, but is rate-limited per IP).")
    style = st.session_state.get("mirror_style", "Lens (focal lines)")
    if style.startswith("Lens"):
        _nla = st.session_state.get("nla_result")
        _pr = (_nla.prompt if _nla is not None else "") or ""
        lens_scene = npc.build_lens_scene(
            _pr, None, _nla,
            {"ok": scene["meta"].get("attrib_ok", False),
             "nodes": scene.get("tree", {}).get("nodes", [])},
            answer=answer,
        )
        components.html(lens_html(lens_scene), height=_lens_height(), scrolling=False)
    else:
        components.html(mise_en_abime_html(scene, np_url=np_url),
                        height=_scene_height(scene), scrolling=True)


# --- Run mirror ---

if mirror_btn:
    if not prompt.strip():
        st.warning("Enter a prompt in the sidebar first.")
    else:
        _mp_area = st.empty()
        _sys = knowledge_layer if nla_include_system else None
        with st.spinner(f"Reading {nla_model}'s activations, token by token…"):
            def _mp(done, total):
                _mp_area.progress(done / total, text=f"Verbalizing tokens · {done}/{total}")
            st.session_state["nla_result"] = npc.verbalize_activations(
                prompt, model=nla_model, source=nla_source, system=_sys,
                max_tokens=nla_max_tokens, progress=_mp,
            )
        _mp_area.empty()
        with st.spinner("Tracing the attribution circuit, then assembling the scene…"):
            _scene, _np_url, _attrib = compute_scene(
                prompt, (knowledge_layer if nla_include_system else None),
                st.session_state["nla_result"], trace_attrib,
            )
        st.session_state["scene"] = _scene
        st.session_state["scene_np_url"] = _np_url
        st.session_state["scene_attrib_status"] = _attrib

scene = st.session_state.get("scene")
if scene is not None:
    st.markdown("### 🪞 Borges Graph")
    render_scene(scene, st.session_state.get("scene_np_url", ""),
                 st.session_state.get("scene_attrib_status"))
