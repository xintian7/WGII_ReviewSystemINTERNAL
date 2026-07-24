from pathlib import Path

import streamlit as st


def render_user_guide_page() -> None:
    st.divider()
    st.markdown("# User Guide")

    guide_path = Path(__file__).resolve().parent / "userGuide.md"
    if guide_path.exists():
        st.markdown(guide_path.read_text(encoding="utf-8"))
    else:
        st.warning("userGuide.md not found.")
