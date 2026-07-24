# Streamlit Layout Clone Template

Use this guide to create a new Streamlit app folder with the same shell layout as Climate Literature Navigator, while keeping all page content empty.

## 1. Layout and design spec

### Typography
- Primary app font: Source Sans Pro, sans-serif (matches Streamlit default style)
- Main title size: 42px
- Notice banner size: 17px
- Sidebar brand text: bold, cyan

### Color palette
- Brand cyan: #00A9CF
- Info banner background: #EAF4FF
- Info banner border: #BBDFFF
- Info banner text: #1F2D3D
- Primary button: #1F77B4
- Primary button hover: #166AA3
- Secondary/disabled gray: #A3A3A3
- Secondary hover gray: #8A8A8A
- Sidebar selected tab background: rgba(0, 169, 207, 0.28)
- Sidebar selected tab border: rgba(0, 169, 207, 0.65)
- Sidebar hover background: rgba(0, 169, 207, 0.16)

### Sidebar tab groups
Read information
- about
- disclaimer
- user guide
- give feedback
- other apps
- to do

Find Literature
- litereature search
- literature analysis
- literature review
- literature network
- literature export
- settings

## 2. Create a new app folder

Example folder name: WG2_layout_clone

```bash
mkdir -p WG2_layout_clone/pages WG2_layout_clone/.streamlit
```

## 3. Create files

### 3.1 .streamlit/config.toml

Path: WG2_layout_clone/.streamlit/config.toml

```toml
[client]
showSidebarNavigation = false

[server]
fileWatcherType = "poll"
runOnSave = true
```

### 3.2 pages/__init__.py

Path: WG2_layout_clone/pages/__init__.py

```python
from .about_page import render_about_page
from .disclaimer_page import render_disclaimer_page
from .user_guide_page import render_user_guide_page
from .give_feedback_page import render_give_feedback_page
from .other_apps_page import render_other_apps_page
from .todo_page import render_todo_page
from .settings_page import render_settings_page
from .literature_search_page import render_literature_search_page
from .literature_analysis_page import render_literature_analysis_page
from .literature_review_page import render_literature_review_page
from .literature_network_page import render_literature_network_page
from .literature_export_page import render_literature_export_page
```

### 3.3 Empty page modules

Create these files under WG2_layout_clone/pages and keep them empty-content placeholders:

- about_page.py
- disclaimer_page.py
- user_guide_page.py
- give_feedback_page.py
- other_apps_page.py
- todo_page.py
- settings_page.py
- literature_search_page.py
- literature_analysis_page.py
- literature_review_page.py
- literature_network_page.py
- literature_export_page.py

Use this same minimal template in each file (change function name per filename):

```python
import streamlit as st


def render_about_page() -> None:
    st.divider()
    st.markdown("# About")
```

Function name mapping:
- about_page.py -> render_about_page
- disclaimer_page.py -> render_disclaimer_page
- user_guide_page.py -> render_user_guide_page
- give_feedback_page.py -> render_give_feedback_page
- other_apps_page.py -> render_other_apps_page
- todo_page.py -> render_todo_page
- settings_page.py -> render_settings_page
- literature_search_page.py -> render_literature_search_page
- literature_analysis_page.py -> render_literature_analysis_page
- literature_review_page.py -> render_literature_review_page
- literature_network_page.py -> render_literature_network_page
- literature_export_page.py -> render_literature_export_page

### 3.4 app.py (full shell with empty-content routing)

Path: WG2_layout_clone/app.py

```python
import streamlit as st

from pages import (
    render_about_page,
    render_disclaimer_page,
    render_user_guide_page,
    render_give_feedback_page,
    render_other_apps_page,
    render_todo_page,
    render_settings_page,
    render_literature_analysis_page,
    render_literature_review_page,
    render_literature_network_page,
    render_literature_export_page,
    render_literature_search_page,
)


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
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 1px;
}

section.main > div.block-container {
    padding-left: 20%;
    padding-right: 20%;
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

st.markdown('<div class="main-title"> Climate Literature Navigator </div>', unsafe_allow_html=True)

if "sidebar_info_section" not in st.session_state:
    st.session_state["sidebar_info_section"] = "about"
if "sidebar_main_section" not in st.session_state:
    st.session_state["sidebar_main_section"] = None
if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "info:about"


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
    st.markdown(
        "<span style='color: #00a9cf; font-weight: bold;'>Climate Literature Navigator (ver 0.4)</span>",
        unsafe_allow_html=True,
    )
    st.markdown("Read information")

    info_icon_map = {
        "about": "ℹ️ About",
        "disclaimer": "⚠️ Disclaimer",
        "user guide": "📘 User Guide",
        "give feedback": "💬 Give Feedback",
        "other apps": "🧩 Other Apps",
        "to do": "✅ Development Plan",
    }

    main_icon_map = {
        "settings": "⚙️ Settings",
        "litereature search": "🔎 Litereature Search",
        "literature analysis": "📊 Literature Analysis",
        "literature review": "📑 Literature Review",
        "literature network": "🔗 Literature Network",
        "literature export": "📤 Literature Export",
    }

    st.radio(
        "",
        options=["about", "disclaimer", "user guide", "give feedback", "other apps", "to do"],
        index=None,
        key="sidebar_info_section",
        label_visibility="collapsed",
        on_change=_on_info_section_change,
        format_func=lambda label: info_icon_map.get(label, label.title()),
    )

    st.divider()

    st.markdown("Find Literature")

    st.radio(
        "",
        options=["litereature search", "literature analysis", "literature review", "literature network", "literature export", "settings"],
        index=None,
        key="sidebar_main_section",
        label_visibility="collapsed",
        on_change=_on_main_section_change,
        format_func=lambda label: main_icon_map.get(label, label.title()),
    )

active_panel = st.session_state.get("active_panel", "info:about")

if active_panel == "info:about":
    render_about_page()
    st.stop()

if active_panel == "info:disclaimer":
    render_disclaimer_page()
    st.stop()

if active_panel == "info:user guide":
    render_user_guide_page()
    st.stop()

if active_panel == "info:give feedback":
    render_give_feedback_page()
    st.stop()

if active_panel == "info:other apps":
    render_other_apps_page()
    st.stop()

if active_panel == "info:to do":
    render_todo_page()
    st.stop()

active_main_section = st.session_state.get("sidebar_main_section")

if active_main_section == "literature analysis":
    render_literature_analysis_page()
    st.stop()

if active_main_section == "literature review":
    render_literature_review_page()
    st.stop()

if active_main_section == "literature network":
    render_literature_network_page()
    st.stop()

if active_main_section == "literature export":
    render_literature_export_page()
    st.stop()

if active_main_section == "settings":
    render_settings_page()
    st.stop()

render_literature_search_page()
```

## 4. Run the new app

From repository root:

```bash
streamlit run WG2_layout_clone/app.py
```

## 5. Optional adjustments

- If you want the same visual style but a different title, update only the text inside .main-title.
- If you want a wider content area, reduce left/right padding from 20% to 15%.
- If you want larger sidebar labels, increase padding and line-height in sidebar radio label CSS.

## 6. API integration parity (Notion and OpenAI)

This section explains how to make the new app call Notion and OpenAI in the same style as the current project.

### 6.1 Environment variables

Add these variables to your environment or .env file in the new app folder:

- NOTION_TOKEN
- DATABASE_ID
- literature_database_id
- OPENAI_API_KEY
- OPENAI_MODEL

Notes:
- In the current app, Notion logging uses DATABASE_ID for feedback and literature_database_id for search logs.
- OPENAI is not currently wired in this repository; the pattern below adds it in a way consistent with existing service helpers.

Suggested values:
- OPENAI_MODEL=gpt-4o-mini

### 6.2 Folder additions for API services

Create these files in the new app folder:

- WG2_layout_clone/services/notion_client.py
- WG2_layout_clone/services/notion_logging_service.py
- WG2_layout_clone/services/openai_client.py
- WG2_layout_clone/services/openai_text_service.py

Create an init file:

- WG2_layout_clone/services/__init__.py

### 6.3 Notion call flow (same as current app)

Current pattern in this repository:

1. UI/page function calls write_feedback_to_notion or write_search_log_to_notion.
2. Service function reads credentials from environment.
3. Service function builds Notion properties payload.
4. Service function calls low-level create_notion_page.
5. Function returns a tuple: (ok: bool, message: str).
6. Search log writes can queue to local JSONL on transient network/proxy/SSL failures.

Use this exact low-level client in WG2_layout_clone/services/notion_client.py:

```python
"""Low-level Notion API client helpers."""

from typing import Any

import requests


NOTION_PAGES_URL = "https://api.notion.com/v1/pages"
NOTION_API_VERSION = "2022-06-28"


def create_notion_page(
    token: str,
    database_id: str,
    properties: dict[str, Any],
) -> tuple[bool, object]:
    """Create a Notion page in the target database and return raw response detail on failure."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": database_id.strip()},
        "properties": properties,
    }

    def _post_page(*, bypass_env_proxy: bool) -> requests.Response:
        if bypass_env_proxy:
            with requests.Session() as session:
                session.trust_env = False
                return session.post(
                    NOTION_PAGES_URL,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
        return requests.post(
            NOTION_PAGES_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

    try:
        response = _post_page(bypass_env_proxy=False)
    except requests.exceptions.ProxyError:
        try:
            response = _post_page(bypass_env_proxy=True)
        except requests.RequestException as exc:
            return False, f"Request error after proxy bypass retry: {exc}"
    except requests.RequestException as exc:
        return False, f"Request error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"

    if response.status_code >= 300:
        try:
            return False, response.json()
        except ValueError:
            return False, response.text

    return True, "ok"
```

Then copy the application-level logger from the current app into WG2_layout_clone/services/notion_logging_service.py, and keep the same public function signatures:

- write_feedback_to_notion(...)
- write_search_log_to_notion(...)

Both should return:

- Success: (True, "...")
- Failure: (False, "...")

### 6.4 OpenAI call flow (matching Notion service style)

To keep behavior consistent, use the same service contract style as Notion:

1. UI/page function calls a high-level helper (for example summarize_with_openai).
2. Helper validates env vars and payload.
3. Helper calls a low-level API client.
4. Helper returns tuple (ok: bool, data_or_message).
5. UI renders success with st.success or result text, and failures with st.warning/st.error.

Install package in the new app environment:

```bash
pip install openai
```

Create WG2_layout_clone/services/openai_client.py:

```python
"""Low-level OpenAI API client helper."""

import os
from typing import Any

from openai import OpenAI


def request_openai_text(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 800,
) -> tuple[bool, Any]:
    """Return (ok, response_text_or_error_detail)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False, "OPENAI_API_KEY is missing in environment variables."

    chosen_model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=chosen_model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        text = getattr(response, "output_text", "")
        if text and str(text).strip():
            return True, str(text).strip()
        return False, "OpenAI returned an empty response."
    except Exception as exc:
        return False, f"OpenAI request failed: {exc}"
```

Create WG2_layout_clone/services/openai_text_service.py:

```python
"""Application-level OpenAI text services."""

from services.openai_client import request_openai_text


def summarize_with_openai(text: str) -> tuple[bool, str]:
    """Summarize user text using OpenAI and return (ok, result_or_error)."""
    content = (text or "").strip()
    if not content:
        return False, "No text provided for summarization."

    prompt = (
        "Summarize the following text in 5 concise bullet points. "
        "Keep names, dates, and numbers accurate.\n\n"
        f"Text:\n{content}"
    )

    ok, detail = request_openai_text(prompt)
    if not ok:
        return False, str(detail)
    return True, str(detail)
```

### 6.5 Example UI usage pattern (same style for both APIs)

Use this in any page module to keep API calls consistent:

```python
import streamlit as st

from services.notion_logging_service import write_feedback_to_notion
from services.openai_text_service import summarize_with_openai


def render_example_api_page() -> None:
    st.divider()
    st.markdown("# API Integration Example")

    user_text = st.text_area("Input text", value="", height=140)

    if st.button("Summarize with OpenAI", type="primary"):
        ok, detail = summarize_with_openai(user_text)
        if ok:
            st.success("OpenAI call succeeded.")
            st.markdown(detail)
        else:
            st.error(detail)

    if st.button("Send test feedback to Notion"):
        ok, msg = write_feedback_to_notion(
            name="Template User",
            chapter="",
            email="",
            message="This is a template test message.",
            contact_ok=False,
        )
        if ok:
            st.success(msg)
        else:
            st.warning(msg)
```

### 6.6 Migration checklist

- Copy Notion helper files and keep the same function signatures.
- Add OPENAI_API_KEY and OPENAI_MODEL to your environment.
- Add openai to dependencies.
- Use tuple returns (ok, message_or_data) for both Notion and OpenAI services.
- Keep API-specific errors inside service modules, and show user-friendly messages in page modules.
