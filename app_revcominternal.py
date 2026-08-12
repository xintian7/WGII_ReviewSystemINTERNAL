import streamlit as st

from pageFilterComments import render_comment_analysis_tab, render_fod_ch1_tab
from pageDevelopmentPlan import render_todo_page
from pageSetting import (
    initialize_auth_state,
    is_auth_unlocked,
    render_setting_page,
    use_ch1_title_variant,
)
from pageUserGuide import render_user_guide_page


# ---------- Placeholder page renderers ----------
def render_about_page() -> None:
    st.divider()
    st.markdown("# About")


def render_disclaimer_page() -> None:
    st.divider()
    st.markdown("# Disclaimer")


def render_give_feedback_page() -> None:
    st.divider()
    st.markdown("# Give Feedback")


def render_other_apps_page() -> None:
    st.divider()
    st.markdown("# Other Apps")


def render_comment_analysis_page() -> None:
    render_comment_analysis_tab()


def render_fod_ch1_page() -> None:
    render_fod_ch1_tab()


st.markdown(
    """
<style>
footer {
    visibility: hidden;
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none;
}

[data-testid="stSidebarNav"] {
    display: none;
}

:root {
    --brand-cyan: #00A9CF;
    --info-bg: #EAF4FF;
    --info-border: #BBDFFF;
    --info-text: #1F2D3D;
    --primary-btn: #1F77B4;
    --primary-btn-hover: #166AA3;
    --secondary-btn: #A3A3A3;
    --secondary-btn-hover: #8A8A8A;
}

html, body, [class*="css"] {
    font-family: "Source Sans Pro", sans-serif;
}

.main-title {
    color: var(--brand-cyan);
    padding: 6px 0 2px 0;
    margin: 0;
    border-radius: 10px;
    text-align: center;
    line-height: 1.12;
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 1px;
}

div[data-testid="stMarkdownContainer"]:has(.main-title) {
    margin-bottom: 0 !important;
}

section.main > div.block-container hr {
    margin-top: 0.2rem;
    margin-bottom: 0.55rem;
}

section.main > div.block-container {
    padding-left: 20%;
    padding-right: 20%;
    font-size: 0.875rem;
}

section.main div.block-container h1,
section.main div.block-container h2,
section.main div.block-container h3 {
    text-align: center;
}

div.stButton > button[kind="primary"] {
    background-color: var(--primary-btn);
    color: #ffffff;
    border: 1px solid var(--primary-btn);
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}

div.stButton > button[kind="primary"]:hover {
    background-color: var(--primary-btn-hover);
    border-color: var(--primary-btn-hover);
}

div.stButton > button[kind="secondary"] {
    background-color: var(--secondary-btn);
    color: #ffffff;
    border: 1px solid var(--secondary-btn);
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}

div.stButton > button[kind="secondary"]:hover {
    background-color: var(--secondary-btn-hover);
    border-color: var(--secondary-btn-hover);
}

div.stButton > button[kind="primary"]:disabled {
    background-color: var(--secondary-btn);
    color: #ffffff;
    border-color: var(--secondary-btn);
    cursor: not-allowed;
}

div.stDownloadButton > button {
    background-color: var(--primary-btn);
    color: #ffffff;
    border: 1px solid var(--primary-btn);
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}

div.stDownloadButton > button:hover {
    background-color: var(--primary-btn-hover);
    border-color: var(--primary-btn-hover);
}

div[data-testid="stCaptionContainer"] strong {
    color: var(--brand-cyan) !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

div[data-testid="stCaptionContainer"] a,
div[data-testid="stCaptionContainer"] a:link,
div[data-testid="stCaptionContainer"] a:visited,
div[data-testid="stCaptionContainer"] a:hover,
div[data-testid="stCaptionContainer"] a:active {
    color: var(--brand-cyan) !important;
    font-weight: 700 !important;
    text-decoration-thickness: 2px;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="radio"] > div:first-child,
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
section[data-testid="stSidebar"] div[role="radiogroup"] label [aria-checked] {
    display: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 3px 8px !important;
    border-radius: 6px !important;
    margin-bottom: 1px !important;
    min-height: 0 !important;
    line-height: 1.15 !important;
    transition: background-color 0.15s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background-color: rgba(0, 169, 207, 0.28) !important;
    border: 1px solid rgba(0, 169, 207, 0.65) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: rgba(0, 169, 207, 0.16);
}

section[data-testid="stSidebar"] hr {
    margin: 0.45rem 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

if "sidebar_info_section" not in st.session_state:
    st.session_state["sidebar_info_section"] = None
if "sidebar_main_section" not in st.session_state:
    st.session_state["sidebar_main_section"] = "setting"
if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "main:setting"
initialize_auth_state()
is_unlocked = is_auth_unlocked()

if not is_unlocked:
    st.session_state["sidebar_info_section"] = None
    st.session_state["sidebar_main_section"] = "setting"
    st.session_state["active_panel"] = "main:setting"

use_ch1_title = is_unlocked and use_ch1_title_variant()

if is_unlocked and use_ch1_title and st.session_state.get("sidebar_main_section") not in {"fod ch1", "setting"}:
    st.session_state["sidebar_info_section"] = None
    st.session_state["sidebar_main_section"] = "fod ch1"
    st.session_state["active_panel"] = "main:fod ch1"

if use_ch1_title:
    page_title_html = '<div class="main-title">Review Comment Panel</div>'
    sidebar_title_html = "<span style='color: #00a9cf; font-weight: bold;'>Review Comment Panel</span>"
else:
    page_title_html = '<div class="main-title">Review Comment Panel<br><span style="font-size:38px;">Internal Use for WGII</span></div>'
    sidebar_title_html = "<span style='color: #00a9cf; font-weight: bold;'>Review Comment Panel<br>Internal Use for WGII</span>"

st.markdown(page_title_html, unsafe_allow_html=True)


def _on_info_section_change() -> None:
    selected_info = st.session_state.get("sidebar_info_section")
    st.session_state["sidebar_main_section"] = None
    if selected_info:
        st.session_state["active_panel"] = f"info:{selected_info}"


def _on_main_section_change() -> None:
    selected_main = st.session_state.get("sidebar_main_section")
    if selected_main:
        st.session_state["sidebar_info_section"] = None
        st.session_state["active_panel"] = f"main:{selected_main}"


with st.sidebar:
    st.markdown(sidebar_title_html, unsafe_allow_html=True)
    main_icon_map = {
        "comment analysis": "Filter Comments",
        "fod ch1": "FOD-Ch1",
        "setting": "Setting",
    }

    if is_unlocked:
        if use_ch1_title:
            st.divider()
            st.markdown("Review Comment Analysis")
            st.radio(
                "",
                options=["fod ch1", "setting"],
                index=None,
                key="sidebar_main_section",
                label_visibility="collapsed",
                on_change=_on_main_section_change,
                format_func=lambda label: main_icon_map.get(label, label.title()),
            )
        else:
            st.markdown("Read information")

            info_icon_map = {
                "user guide": "User Guide",
                "to do": "Development Plan",
            }

            st.radio(
                "",
                options=["user guide", "to do"],
                index=None,
                key="sidebar_info_section",
                label_visibility="collapsed",
                on_change=_on_info_section_change,
                format_func=lambda label: info_icon_map.get(label, label.title()),
            )

            st.divider()

            st.markdown("Review Comment Analysis")

            st.radio(
                "",
                options=["comment analysis", "fod ch1", "setting"],
                index=None,
                key="sidebar_main_section",
                label_visibility="collapsed",
                on_change=_on_main_section_change,
                format_func=lambda label: main_icon_map.get(label, label.title()),
            )
    else:
        st.markdown("Review Comment Analysis")
        st.radio(
            "",
            options=["setting"],
            index=0,
            key="sidebar_main_section",
            label_visibility="collapsed",
            format_func=lambda label: main_icon_map.get(label, label.title()),
        )

active_panel = st.session_state.get("active_panel", "main:setting")
active_main_section = st.session_state.get("sidebar_main_section")

if active_main_section == "setting" or active_panel == "main:setting":
    render_setting_page()
    st.stop()

if not is_unlocked:
    st.stop()

if active_panel == "info:user guide":
    render_user_guide_page()
    st.stop()

if active_panel == "info:to do":
    render_todo_page()
    st.stop()

if active_main_section == "fod ch1":
    render_fod_ch1_page()
    st.stop()

if active_main_section == "comment analysis":
    render_comment_analysis_page()
    st.stop()

if active_main_section == "setting":
    render_setting_page()
    st.stop()

render_comment_analysis_page()
