import ast
import os
from pathlib import Path

import streamlit as st


def _env_candidates() -> list[Path]:
    base_dir = Path(__file__).resolve().parent
    return [
        Path(".env"),
        base_dir / ".env",
        base_dir.parent / ".env",
    ]


def _load_env_file_if_present(env_path: Path, *, overwrite: bool = False) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if overwrite or key not in os.environ:
            os.environ[key] = value


def _get_allowed_passwords() -> list[str]:
    # Always refresh password vars from .env so updates take effect immediately.
    for env_path in _env_candidates():
        _load_env_file_if_present(env_path, overwrite=True)

    raw = (os.getenv("user_pwd") or os.getenv("USER_PWD") or "").strip()
    if not raw:
        return []

    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, (list, tuple, set)):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (SyntaxError, ValueError):
        pass

    # Fallback for comma-separated format.
    return [x.strip() for x in raw.split(",") if x.strip()]


def _validate_password() -> None:
    entered = str(st.session_state.get("setting_pwd_input", "")).strip()
    allowed = _get_allowed_passwords()
    matched_password = next((pwd for pwd in allowed if entered and entered == pwd), "")
    st.session_state["auth_unlocked"] = bool(matched_password)
    st.session_state["auth_has_ch1_pwd"] = bool(
        matched_password and "ch1" in matched_password.lower()
    )
    # Clear typed password from session state after validation.
    st.session_state["setting_pwd_input"] = ""
    if st.session_state["auth_unlocked"]:
        st.session_state["sidebar_info_section"] = None
        if st.session_state["auth_has_ch1_pwd"]:
            st.session_state["sidebar_main_section"] = "fod ch1"
            st.session_state["active_panel"] = "main:fod ch1"
        else:
            st.session_state["sidebar_main_section"] = "comment analysis"
            st.session_state["active_panel"] = "main:comment analysis"


def initialize_auth_state() -> None:
    if "setting_pwd_input" not in st.session_state:
        st.session_state["setting_pwd_input"] = ""
    if "auth_unlocked" not in st.session_state:
        st.session_state["auth_unlocked"] = False
    if "auth_has_ch1_pwd" not in st.session_state:
        st.session_state["auth_has_ch1_pwd"] = False


def is_auth_unlocked() -> bool:
    return bool(st.session_state.get("auth_unlocked", False))


def use_ch1_title_variant() -> bool:
    return bool(st.session_state.get("auth_has_ch1_pwd", False))


def render_setting_page() -> None:
    initialize_auth_state()

    st.divider()
    st.markdown("# Setting")

    st.text_input(
        "Password",
        key="setting_pwd_input",
        type="password",
        placeholder="Enter password to unlock",
    )
    st.button("Validate Password", type="primary", on_click=_validate_password)

    if is_auth_unlocked():
        st.success("Password accepted. All functionality is enabled.")
    else:
        st.warning("Invalid or missing password. App functionality remains disabled.")
