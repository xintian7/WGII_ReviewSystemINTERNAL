import base64
import hashlib
import html
import io
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet


PAGE_SIZE_OPTIONS = [5, 10, 20, 50]
DEFAULT_PAGE_SIZE = 10
DEFAULT_COMMENT_SEARCH = "applicab*"
FERNET_KEY_ENV = "FERNET_KEY"
SPM_CHAPTER = "Summary for Policymakers"
SPM_SECTION_UI_OPTIONS = ["Introduction", "A", "B", "C", "D", "The whole SPM"]
EXPORT_EXCLUDED_COLUMNS = [
    "res_p1",
    "res_p2",
    "res_p3",
    "res_p4",
    "res_p5",
    "primary_result",
    "primary_org",
    "primary_method",
    "primary_confidence",
    "unknown_orgs",
    "gpt_unknown_types",
]

DEFAULT_REQUIRED_COLUMNS = [
    "commentid",
    "chapter",
    "category",
    "subcategory",
    "isfp",
    "primary_result_after_gpt",
    "comment",
    "affiliation",
    "country",
    "reviewerfirstname",
    "reviewerlastname",
    "Action",
    "frompage",
    "topage",
]

CANONICAL_COLUMN_ALIASES = {
    "commentid": ["commentid", "comment_id"],
    "chapter": ["chapter"],
    "category": ["category"],
    "subcategory": ["subcategory"],
    "isfp": ["isfp", "nationalfocalpoint", "nfp"],
    "primary_result_after_gpt": [
        "primaryresultaftergpt",
        "affiliationtype",
        "affiliationtypegpt",
    ],
    "comment": ["comment", "comments"],
    "affiliation": ["affiliation", "institution"],
    "country": ["country"],
    "reviewerfirstname": ["reviewerfirstname", "firstname", "reviewerfirst"],
    "reviewerlastname": ["reviewerlastname", "lastname", "reviewerlast"],
    "Action": ["action", "categoryofresponse", "responsecategory", "reponsetocomments", "responsetocomments"],
    "frompage": ["frompage", "pagefrom"],
    "topage": ["topage", "pageto"],
}


def _state_key(prefix: str, key: str) -> str:
    p = str(prefix or "review").strip()
    return f"{p}_{key}"


def _normalize_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _apply_canonical_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()

    normalized_to_actual: dict[str, str] = {}
    for col in renamed.columns:
        token = _normalize_token(col)
        if token and token not in normalized_to_actual:
            normalized_to_actual[token] = col

    rename_map: dict[str, str] = {}
    for canonical, alias_tokens in CANONICAL_COLUMN_ALIASES.items():
        if canonical in renamed.columns:
            continue
        for alias in alias_tokens:
            actual = normalized_to_actual.get(_normalize_token(alias))
            if actual and actual not in rename_map:
                rename_map[actual] = canonical
                break

    if rename_map:
        renamed = renamed.rename(columns=rename_map)

    return renamed


def _initial_applied_filters() -> dict[str, object]:
    return {
        "chapters": [],
        "sections": [],
        "nfp": "",
        "categories": [],
        "subcategories": [],
        "aff_types": [],
        "comment_search": DEFAULT_COMMENT_SEARCH,
        "aff_country_search": "",
    }


def _reset_comment_analysis_state(prefix: str = "review", default_chapter: str | None = None) -> None:
    st.session_state[_state_key(prefix, "show_comments")] = False
    st.session_state[_state_key(prefix, "page_index")] = 0
    st.session_state[_state_key(prefix, "page_size")] = DEFAULT_PAGE_SIZE
    st.session_state[_state_key(prefix, "applied_filters")] = {
        "chapters": [],
        "sections": [],
        "nfp": "",
        "categories": [],
        "subcategories": [],
        "aff_types": [],
        "comment_search": "",
        "aff_country_search": "",
    }

    st.session_state[_state_key(prefix, "filter_chapters")] = [default_chapter] if default_chapter else []
    st.session_state[_state_key(prefix, "filter_sections")] = []
    st.session_state[_state_key(prefix, "filter_nfp")] = ""
    st.session_state[_state_key(prefix, "filter_aff_types")] = []
    st.session_state[_state_key(prefix, "filter_categories")] = []
    st.session_state[_state_key(prefix, "filter_subcategories")] = []
    st.session_state[_state_key(prefix, "filter_search_comments")] = ""
    st.session_state[_state_key(prefix, "filter_search_aff_country")] = ""
    st.session_state[_state_key(prefix, "chapter_default_applied")] = bool(default_chapter)


def _encrypted_candidates(file_name: str) -> list[Path]:
    base_dir = Path(__file__).resolve().parent
    return [
        Path(f"data/{file_name}"),
        Path(file_name),
        base_dir / "data" / file_name,
        base_dir / file_name,
    ]


def _encrypted_cache_key(file_name: str) -> str:
    enc_path = next((p for p in _encrypted_candidates(file_name) if p.exists()), None)
    if enc_path is None:
        return "missing"
    stat = enc_path.stat()
    return f"{enc_path}:{stat.st_mtime_ns}:{stat.st_size}"


def _env_candidates() -> list[Path]:
    base_dir = Path(__file__).resolve().parent
    return [
        Path(".env"),
        base_dir / ".env",
        base_dir.parent / ".env",
    ]


def _load_env_file_if_present(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


def _build_fernet_from_value(raw_key: str) -> Fernet:
    raw_key = (raw_key or "").strip()
    if not raw_key:
        raise ValueError("Empty key value.")

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        derived_key = base64.urlsafe_b64encode(digest)
        return Fernet(derived_key)


@st.cache_data(show_spinner=False)
def _load_encrypted_dataframe(file_name: str, _cache_key: str = "") -> pd.DataFrame:
    if not os.getenv(FERNET_KEY_ENV):
        for env_path in _env_candidates():
            _load_env_file_if_present(env_path)
            if os.getenv(FERNET_KEY_ENV):
                break

    key = os.getenv(FERNET_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(f"Missing key in environment variable: {FERNET_KEY_ENV}")

    enc_path = next((p for p in _encrypted_candidates(file_name) if p.exists()), None)
    if enc_path is None:
        raise FileNotFoundError(f"{file_name} not found in data/ or project root.")

    encrypted = enc_path.read_bytes()
    parquet_bytes = _build_fernet_from_value(key).decrypt(encrypted)
    df = pd.read_parquet(io.BytesIO(parquet_bytes))
    df = _apply_canonical_column_aliases(df)

    for col in DEFAULT_REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df


def _init_state(prefix: str = "review") -> None:
    defaults = {
        _state_key(prefix, "show_comments"): False,
        _state_key(prefix, "page_index"): 0,
        _state_key(prefix, "page_size"): DEFAULT_PAGE_SIZE,
        _state_key(prefix, "applied_filters"): _initial_applied_filters(),
        _state_key(prefix, "filter_search_comments"): DEFAULT_COMMENT_SEARCH,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _compute_page_tokens(total_pages: int, current_page: int) -> list[int | str]:
    if total_pages <= 4:
        return list(range(1, total_pages + 1))

    tokens: list[int | str] = [1]
    left = max(2, current_page)
    right = min(total_pages - 1, current_page + 2)

    if left > 2:
        tokens.append("...")
    for page in range(left, right + 1):
        tokens.append(page)
    if right < total_pages - 1:
        tokens.append("...")
    tokens.append(total_pages)
    return tokens


def _is_spm_only_selected(chapters: list[str]) -> bool:
    cleaned = [str(x).strip() for x in chapters if str(x).strip()]
    return len(cleaned) == 1 and cleaned[0] == SPM_CHAPTER


def _get_spm_section_options(df: pd.DataFrame) -> list[str]:
    if "spm_section_number" not in df.columns:
        return []
    return SPM_SECTION_UI_OPTIONS.copy()


def _section_tokens_from_value(value: str) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    return {tok.strip() for tok in raw.split("|") if tok.strip()}


def _selected_spm_tokens(selected_sections: list[str]) -> set[str]:
    out: set[str] = set()
    for section in selected_sections:
        s = str(section).strip()
        if not s:
            continue
        if s == "The whole SPM":
            out.add("full")
        else:
            out.add(s)
    return out


def _filter_dataframe(df: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    out = df.copy()

    chapters = list(filters.get("chapters", []))
    sections = list(filters.get("sections", []))
    nfp = str(filters.get("nfp", "")).strip().lower()
    categories = list(filters.get("categories", []))
    subcategories = list(filters.get("subcategories", []))
    aff_types = list(filters.get("aff_types", []))
    comment_search = str(filters.get("comment_search", "")).strip().lower()
    aff_country_search = str(filters.get("aff_country_search", "")).strip().lower()

    if chapters:
        out = out[out["chapter"].isin(chapters)]
    if sections:
        if _is_spm_only_selected(chapters) and "spm_section_number" in out.columns:
            selected_tokens = _selected_spm_tokens(sections)
            if selected_tokens:
                out = out[
                    out["spm_section_number"].fillna("").astype(str).apply(
                        lambda x: (
                            bool(_section_tokens_from_value(x))
                            and _section_tokens_from_value(x).issubset(selected_tokens)
                        )
                    )
                ]
    if nfp:
        isfp_numeric = pd.to_numeric(out["isfp"], errors="coerce")
        if nfp == "yes":
            out = out[isfp_numeric == 1]
        elif nfp == "no":
            out = out[isfp_numeric == 0]
    if categories:
        out = out[out["category"].isin(categories)]
    if subcategories:
        out = out[out["subcategory"].isin(subcategories)]
    if aff_types:
        out = out[out["primary_result_after_gpt"].isin(aff_types)]

    if comment_search:
        comment_text = out["comment"].fillna("").astype(str).str.lower()
        out = out[_build_boolean_mask(comment_text, comment_search)]

    if aff_country_search:
        aff_text = out["affiliation"].fillna("").astype(str).str.lower()
        country_text = out["country"].fillna("").astype(str).str.lower()
        reviewer_first = out["reviewerfirstname"].fillna("").astype(str).str.lower()
        reviewer_last = out["reviewerlastname"].fillna("").astype(str).str.lower()
        reviewer_full = (reviewer_first.str.strip() + " " + reviewer_last.str.strip()).str.strip()
        out = out[
            _build_boolean_mask(aff_text, aff_country_search)
            | _build_boolean_mask(country_text, aff_country_search)
            | _build_boolean_mask(reviewer_first, aff_country_search)
            | _build_boolean_mask(reviewer_last, aff_country_search)
            | _build_boolean_mask(reviewer_full, aff_country_search)
        ]

    return out.reset_index(drop=True)


def _term_to_regex(term: str) -> str:
    t = str(term or "").strip()
    if not t:
        return ""

    # Quoted terms are treated as exact tokens/phrases and should not match inside larger words.
    if len(t) >= 2 and t.startswith('"') and t.endswith('"'):
        inner = t[1:-1]
        if not inner:
            return ""
        escaped = re.escape(inner)
        left_boundary = r"(?<![A-Za-z0-9_])" if re.match(r"\w", inner[0]) else ""
        right_boundary = r"(?![A-Za-z0-9_])" if re.search(r"\w$", inner) else ""
        return f"{left_boundary}{escaped}{right_boundary}"

    if re.fullmatch(r"\*+", t):
        return r".+"
    return re.escape(t).replace(r"\*", r".*")


def _build_boolean_mask(text_series: pd.Series, query: str) -> pd.Series:
    q = str(query or "").strip()
    if not q:
        return pd.Series([True] * len(text_series), index=text_series.index)

    upper_q = q.upper()
    has_boolean = " AND " in f" {upper_q} " or " OR " in f" {upper_q} "
    if not has_boolean:
        return text_series.str.contains(_term_to_regex(q), regex=True, na=False)

    # OR groups, each with AND-required terms: "a AND b OR c".
    or_groups = [g.strip() for g in re.split(r"\s+OR\s+", q, flags=re.IGNORECASE) if g.strip()]
    group_masks: list[pd.Series] = []
    for group in or_groups:
        and_terms = [t.strip() for t in re.split(r"\s+AND\s+", group, flags=re.IGNORECASE) if t.strip()]
        if not and_terms:
            continue

        and_mask = pd.Series([True] * len(text_series), index=text_series.index)
        for term in and_terms:
            and_mask &= text_series.str.contains(_term_to_regex(term), regex=True, na=False)
        group_masks.append(and_mask)

    if not group_masks:
        return pd.Series([True] * len(text_series), index=text_series.index)

    out = pd.Series([False] * len(text_series), index=text_series.index)
    for gm in group_masks:
        out |= gm
    return out


def _dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    export_df = df.drop(columns=[c for c in EXPORT_EXCLUDED_COLUMNS if c in df.columns], errors="ignore")
    output = io.BytesIO()
    with pd.ExcelWriter(output) as writer:
        export_df.to_excel(writer, index=False, sheet_name="filtered_results")
    output.seek(0)
    return output.getvalue()


def _highlight_text(text: str, keyword: str) -> str:
    raw_text = str(text or "")
    needle = str(keyword or "").strip()
    if not needle:
        return html.escape(raw_text)

    upper_needle = needle.upper()
    if " AND " in f" {upper_needle} " or " OR " in f" {upper_needle} ":
        terms = [
            t.strip()
            for t in re.split(r"\s+(?:AND|OR)\s+", needle, flags=re.IGNORECASE)
            if t.strip()
        ]
        if not terms:
            return html.escape(raw_text)
        pattern = re.compile("|".join(_term_to_regex(t) for t in terms), flags=re.IGNORECASE)
    else:
        pattern = re.compile(_term_to_regex(needle), flags=re.IGNORECASE)
    parts: list[str] = []
    last_end = 0
    for match in pattern.finditer(raw_text):
        start, end = match.span()
        if start > last_end:
            parts.append(html.escape(raw_text[last_end:start]))
        parts.append(f"<mark>{html.escape(raw_text[start:end])}</mark>")
        last_end = end

    if last_end < len(raw_text):
        parts.append(html.escape(raw_text[last_end:]))

    if not parts:
        return html.escape(raw_text)
    return "".join(parts)


def _render_card(row: pd.Series, comment_keyword: str = "") -> None:
    chapter = html.escape(str(row.get("chapter", "")))
    category = html.escape(str(row.get("category", "")))
    subcategory = html.escape(str(row.get("subcategory", "")))
    aff_type = html.escape(str(row.get("primary_result_after_gpt", "")))
    affiliation = html.escape(str(row.get("affiliation", "")))
    country = html.escape(str(row.get("country", "")))
    isfp_val = pd.to_numeric(pd.Series([row.get("isfp", "")]), errors="coerce").iloc[0]
    if pd.isna(isfp_val):
        nfp = ""
    elif int(isfp_val) == 1:
        nfp = "Yes"
    elif int(isfp_val) == 0:
        nfp = "No"
    else:
        nfp = ""
    nfp = html.escape(nfp)
    action = html.escape(str(row.get("Action", "")))
    commentid = html.escape(str(row.get("commentid", "")))
    spm_section = html.escape(str(row.get("spm_section_number", "")).strip())
    frompage = html.escape(str(row.get("frompage", "")))
    topage = html.escape(str(row.get("topage", "")))
    reviewer = html.escape(
        (str(row.get("reviewerfirstname", "")).strip() + " " + str(row.get("reviewerlastname", "")).strip()).strip()
    )
    comment = _highlight_text(str(row.get("comment", "")), comment_keyword)

    st.markdown(
        f"""
        <div class="review-card">
            <div class="review-row"><span class="review-label">Chapter:</span> {chapter}</div>
            <div class="review-row"><span class="review-label">Category:</span> {category} | <span class="review-label">Subcategory (LLM-generated, Reference only):</span> {subcategory}</div>
            <div class="review-row"><span class="review-label">Action (LLM-generated, Reference only):</span> {action}</div>
            <div class="review-row"><span class="review-label">Page Range:</span> {frompage} - {topage} | <span class="review-label">Comment ID:</span> {commentid} | <span class="review-label">SPM Section:</span> {spm_section}</div>
            <div class="review-row"><span class="review-label">Affiliation:</span> {affiliation}</div>
            <div class="review-row"><span class="review-label">Affilation Type (LLM-generated, Reference only):</span> {aff_type}</div>
            <div class="review-row"><span class="review-label">Reviewer:</span> {reviewer} | <span class="review-label">Country:</span> {country} | <span class="review-label">National Focal Point:</span> {nfp}</div>
            <div class="review-row"><span class="review-label">Comment:</span> {comment}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results(filtered: pd.DataFrame, comment_keyword: str = "", prefix: str = "review") -> None:
    total_filtered = len(filtered)
    if total_filtered == 0:
        st.warning("Filtered results: 0")
        return

    page_size = int(st.session_state.get(_state_key(prefix, "page_size"), DEFAULT_PAGE_SIZE))
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = DEFAULT_PAGE_SIZE
        st.session_state[_state_key(prefix, "page_size")] = page_size

    total_pages = max(1, (total_filtered + page_size - 1) // page_size)
    page_index = int(st.session_state.get(_state_key(prefix, "page_index"), 0))
    page_index = max(0, min(page_index, total_pages - 1))
    st.session_state[_state_key(prefix, "page_index")] = page_index

    start = page_index * page_size
    end = min(start + page_size, total_filtered)
    page_df = filtered.iloc[start:end]

    st.caption(
        f"Filtered results:{total_filtered} | Showing {start + 1}-{end} | Page {page_index + 1}/{total_pages}"
    )

    st.markdown('<div class="pagination-row">', unsafe_allow_html=True)
    tokens = _compute_page_tokens(total_pages, page_index + 1)
    pager_items = ["prev", *tokens, "next"]
    pager_cols = st.columns(len(pager_items), gap="small")

    for idx, item in enumerate(pager_items):
        with pager_cols[idx]:
            if item == "prev":
                if st.button(
                    "‹",
                    key=_state_key(prefix, "prev_page"),
                    disabled=page_index == 0,
                    type="secondary",
                    use_container_width=False,
                ):
                    st.session_state[_state_key(prefix, "page_index")] = max(0, page_index - 1)
                    st.rerun()
            elif item == "next":
                if st.button(
                    "›",
                    key=_state_key(prefix, "next_page"),
                    disabled=page_index >= total_pages - 1,
                    type="secondary",
                    use_container_width=False,
                ):
                    st.session_state[_state_key(prefix, "page_index")] = min(total_pages - 1, page_index + 1)
                    st.rerun()
            elif item == "...":
                st.button(
                    "…",
                    key=_state_key(prefix, f"gap_{idx}"),
                    disabled=True,
                    type="secondary",
                    use_container_width=False,
                )
            else:
                is_current = item == (page_index + 1)
                if is_current:
                    st.button(
                        str(item),
                        key=_state_key(prefix, f"page_current_{item}"),
                        disabled=False,
                        type="primary",
                        use_container_width=False,
                    )
                else:
                    if st.button(
                        str(item),
                        key=_state_key(prefix, f"page_{item}"),
                        type="secondary",
                        use_container_width=False,
                    ):
                        st.session_state[_state_key(prefix, "page_index")] = int(item) - 1
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    for _, row in page_df.iterrows():
        _render_card(row, comment_keyword=comment_keyword)


def _render_comment_analysis_base(
    *,
    title: str,
    source_file_name: str,
    state_prefix: str,
    export_file_name: str,
    disable_nfp_filter: bool = False,
    default_to_first_chapter: bool = False,
) -> None:
    _init_state(state_prefix)

    st.markdown(
        """
        <style>
        .review-card {
            background: #FFFFFF;
            border: 1px solid #D9E4EE;
            border-radius: 8px;
            padding: 10px 12px;
            margin: 8px 0 10px 0;
            color: #1F2937;
            line-height: 1.45;
            font-size: 14px;
        }
        .review-row { margin: 2px 0; }
        .review-label {
            color: #1F77B4;
            font-weight: 600;
            font-size: 13px;
        }
        .review-card mark {
            background: #FFE566;
            color: #111111;
            padding: 0 2px;
            border-radius: 2px;
        }

        /* Hide "Press Enter to apply" for the two search fields only. */
        .st-key-__PREFIX___filter_search_comments [data-testid="InputInstructions"],
        .st-key-__PREFIX___filter_search_aff_country [data-testid="InputInstructions"] {
            display: none !important;
        }

        /* Pagination compact override block: keep this after global button CSS. */
        .pagination-row div.stButton {
            display: flex;
            justify-content: flex-start;
            margin-right: -2px;
        }

        .pagination-row [data-testid="column"] {
            padding-left: 1px !important;
            padding-right: 1px !important;
        }

        .st-key-__PREFIX___prev_page button,
        .st-key-__PREFIX___next_page button,
        div[class*="st-key-__PREFIX___gap_"] button,
        div[class*="st-key-__PREFIX___page_"] button,
        div[class*="st-key-__PREFIX___page_current_"] button {
            width: 30px !important;
            min-width: 30px !important;
            max-width: 30px !important;
            min-height: 24px !important;
            height: 24px !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 0.6rem !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            letter-spacing: -0.01em !important;
            border-radius: 5px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Inactive buttons: secondary */
        .st-key-__PREFIX___prev_page button,
        .st-key-__PREFIX___next_page button,
        div[class*="st-key-__PREFIX___page_"] button,
        div[class*="st-key-__PREFIX___gap_"] button {
            background-color: #A3A3A3 !important;
            border: 1px solid #A3A3A3 !important;
            color: #FFFFFF !important;
        }
        .st-key-__PREFIX___prev_page button:hover,
        .st-key-__PREFIX___next_page button:hover,
        div[class*="st-key-__PREFIX___page_"] button:hover {
            background-color: #8A8A8A !important;
            border-color: #8A8A8A !important;
        }

        /* Active page: primary */
        div[class*="st-key-__PREFIX___page_current_"] button {
            background-color: #1F77B4 !important;
            border: 1px solid #1F77B4 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        div[class*="st-key-__PREFIX___page_current_"] button:hover {
            background-color: #166AA3 !important;
            border-color: #166AA3 !important;
        }

        /* Disabled controls: gray and non-interactive. */
        .st-key-__PREFIX___prev_page button:disabled,
        .st-key-__PREFIX___next_page button:disabled,
        div[class*="st-key-__PREFIX___gap_"] button:disabled {
            background-color: #A3A3A3 !important;
            border-color: #A3A3A3 !important;
            color: #FFFFFF !important;
            opacity: 1 !important;
            cursor: not-allowed !important;
        }
        </style>
        """.replace("__PREFIX__", state_prefix),
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown(f"# {title}")

    try:
        df = _load_encrypted_dataframe(source_file_name, _encrypted_cache_key(source_file_name))
    except Exception as exc:
        st.error(f"Failed to load {source_file_name}: {exc}")
        return

    chapters = sorted([x for x in df["chapter"].dropna().astype(str).unique().tolist() if x])
    categories = sorted([x for x in df["category"].dropna().astype(str).unique().tolist() if x])
    subcategories = sorted([x for x in df["subcategory"].dropna().astype(str).unique().tolist() if x])
    aff_types = sorted([x for x in df["primary_result_after_gpt"].dropna().astype(str).unique().tolist() if x])

    chapter_filter_key = _state_key(state_prefix, "filter_chapters")
    chapter_default_applied_key = _state_key(state_prefix, "chapter_default_applied")
    default_chapter = chapters[0] if (default_to_first_chapter and chapters) else None

    if default_chapter and not st.session_state.get(chapter_default_applied_key, False):
        current_chapters = st.session_state.get(chapter_filter_key, [])
        if not current_chapters:
            st.session_state[chapter_filter_key] = [default_chapter]
        st.session_state[chapter_default_applied_key] = True

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        selected_chapters = st.multiselect(
            "Chapters",
            options=chapters,
            default=[],
            key=chapter_filter_key,
        )
    with row1_col2:
        spm_only_selected = _is_spm_only_selected(selected_chapters)
        if spm_only_selected:
            available_sections = _get_spm_section_options(df)
            existing_sections = st.session_state.get(_state_key(state_prefix, "filter_sections"), [])
            if existing_sections:
                st.session_state[_state_key(state_prefix, "filter_sections")] = [
                    x for x in existing_sections if x in available_sections
                ]

            selected_sections = st.multiselect(
                "SPM (sub)sections",
                options=available_sections,
                default=[],
                key=_state_key(state_prefix, "filter_sections"),
                disabled=False,
                help="Available only when Chapters is set to Summary for Policymakers.",
            )
        else:
            if st.session_state.get(_state_key(state_prefix, "filter_sections")):
                st.session_state[_state_key(state_prefix, "filter_sections")] = []
            st.multiselect(
                "SPM (sub)sections",
                options=[],
                default=[],
                key=_state_key(state_prefix, "filter_sections"),
                disabled=True,
                help="Enable this by selecting only Summary for Policymakers in Chapters.",
            )
            selected_sections = []

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        selected_categories = st.multiselect(
            "Categories",
            options=categories,
            default=[],
            key=_state_key(state_prefix, "filter_categories"),
        )
    with row2_col2:
        selected_aff_types = st.multiselect(
            "Affilation type (LLM-categoried)",
            options=aff_types,
            default=[],
            key=_state_key(state_prefix, "filter_aff_types"),
        )

    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        if disable_nfp_filter and st.session_state.get(_state_key(state_prefix, "filter_nfp"), ""):
            st.session_state[_state_key(state_prefix, "filter_nfp")] = ""
        selected_nfp = st.selectbox(
            "National Focal Point",
            options=["", "Yes", "No"],
            key=_state_key(state_prefix, "filter_nfp"),
            disabled=disable_nfp_filter,
            help="Not available for FOD-Ch1 data." if disable_nfp_filter else None,
        )
    with row3_col2:
        if selected_categories:
            available_subcategories = sorted(
                [
                    x
                    for x in df[df["category"].isin(selected_categories)]["subcategory"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                    if x
                ]
            )
        else:
            available_subcategories = subcategories

        existing_subcategories = st.session_state.get(_state_key(state_prefix, "filter_subcategories"), [])
        if existing_subcategories:
            st.session_state[_state_key(state_prefix, "filter_subcategories")] = [
                x for x in existing_subcategories if x in available_subcategories
            ]

        selected_subcategories = st.multiselect(
            "Subcategories (LLM-generated)",
            options=available_subcategories,
            default=[],
            key=_state_key(state_prefix, "filter_subcategories"),
        )

    row4_col1, row4_col2 = st.columns(2)
    with row4_col1:
        search_comments = st.text_input("Search in comments", key=_state_key(state_prefix, "filter_search_comments"))
    with row4_col2:
        search_aff_country = st.text_input(
            "Search in names, affiliations, and countries",
            key=_state_key(state_prefix, "filter_search_aff_country"),
        )

    row5_col1, row5_col2 = st.columns(2)
    with row5_col1:
        st.text_input("Containing URL for reference", value="Under Construction", disabled=True)
    with row5_col2:
        st.text_input("Enable LLM summarization", value="Under Construction", disabled=True)

    row6_col1, row6_col2 = st.columns(2)
    with row6_col1:
        page_size = st.selectbox(
            "Comments per page",
            options=PAGE_SIZE_OPTIONS,
            index=PAGE_SIZE_OPTIONS.index(st.session_state[_state_key(state_prefix, "page_size")]),
        )
    with row6_col2:
        st.write("")

    action_cols = st.columns([1, 1, 1, 5], gap="small")
    with action_cols[0]:
        apply_clicked = st.button("Apply", type="primary", key=_state_key(state_prefix, "apply"))
    with action_cols[1]:
        st.button(
            "Reset",
            type="primary",
            key=_state_key(state_prefix, "reset"),
            on_click=_reset_comment_analysis_state,
            args=(state_prefix, default_chapter),
        )

    if page_size != st.session_state[_state_key(state_prefix, "page_size")]:
        st.session_state[_state_key(state_prefix, "page_size")] = page_size
        st.session_state[_state_key(state_prefix, "page_index")] = 0

    if apply_clicked:
        st.session_state[_state_key(state_prefix, "applied_filters")] = {
            "chapters": selected_chapters,
            "sections": selected_sections,
            "nfp": selected_nfp,
            "categories": selected_categories,
            "subcategories": selected_subcategories,
            "aff_types": selected_aff_types,
            "comment_search": search_comments,
            "aff_country_search": search_aff_country,
        }
        st.session_state[_state_key(state_prefix, "page_index")] = 0
        st.session_state[_state_key(state_prefix, "show_comments")] = True

    filtered = pd.DataFrame()
    if st.session_state[_state_key(state_prefix, "show_comments")]:
        filtered = _filter_dataframe(df, st.session_state[_state_key(state_prefix, "applied_filters")])

    with action_cols[2]:
        if st.session_state[_state_key(state_prefix, "show_comments")] and not filtered.empty:
            st.download_button(
                "Export",
                data=_dataframe_to_excel_bytes(filtered),
                file_name=export_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key=_state_key(state_prefix, "export"),
            )
        else:
            st.button("Export", type="primary", disabled=True, key=_state_key(state_prefix, "export_disabled"))
    with action_cols[3]:
        st.write("")

    if not st.session_state[_state_key(state_prefix, "show_comments")]:
        st.info("Set filters and click Apply to show results.")
        return

    applied_comment_search = str(
        st.session_state[_state_key(state_prefix, "applied_filters")].get("comment_search", "")
    )
    _render_results(filtered, comment_keyword=applied_comment_search, prefix=state_prefix)


def render_comment_analysis_tab() -> None:
    _render_comment_analysis_base(
        title="Filter Comments",
        source_file_name="metadata.parquet.enc",
        state_prefix="review",
        export_file_name="comment_analysis_filtered.xlsx",
        disable_nfp_filter=False,
        default_to_first_chapter=False,
    )


def render_fod_ch1_tab() -> None:
    _render_comment_analysis_base(
        title="FOD-Ch1",
        source_file_name="srfodch1.parquet.enc",
        state_prefix="fodch1",
        export_file_name="fod_ch1_filtered.xlsx",
        disable_nfp_filter=True,
        default_to_first_chapter=True,
    )
