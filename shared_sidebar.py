"""Shared sidebar inputs used by both Canon Ball and Borges Graph pages."""

import streamlit as st


def render_shared_sidebar() -> dict:
    """Draw the prompt and knowledge layer inputs. Returns {"prompt": str, "knowledge_layer": str}."""
    prompt = st.text_area(
        "Prompt · the throw",
        value=st.session_state.get("shared_prompt",
            'Tu vas m\'aider à préparer la course d\'alpinisme "les arêtes du Gerbier" situées dans le Vercors'),
        height=80,
        key="shared_prompt",
    )

    knowledge_layer = st.text_area(
        "Knowledge layer · the ramp",
        value=st.session_state.get("shared_knowledge_layer", """# Definition — Alpine Climbing
Source: Wikidata (Q1759504 — Alpine climbing / Q36908 — Alpinism)

An **alpine climbing route** (course d'alpinisme) is a type of climbing
practiced in high mountains. It is a sub-discipline of alpinism.

## Equipment
- Ice axe, crampons, ice screws
- Climbing gear (ropes, cams, friends)

## Practitioners
Alpine climbing routes are led by **alpinists** (Q9149093)
and supervised by **high mountain guides** (Q819677)."""),
        height=200,
        key="shared_knowledge_layer",
    )

    return {"prompt": prompt, "knowledge_layer": knowledge_layer}
