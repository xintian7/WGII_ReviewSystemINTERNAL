#!/usr/bin/env python3
"""Build SPM section mapping for comment rows using JSON page ranges.

This script reads:
- an SPM structure JSON file (supports a full JSON object or a key:value fragment)
- an Excel workbook containing SPM comments

It outputs:
- spm_structure.xlsx with the selected input sheet plus added section columns.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Section:
    number: str
    name: str
    from_page: int
    to_page: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map SPM comment rows to section numbers based on page ranges."
    )
    parser.add_argument(
        "--json",
        default="spm.json",
        help="SPM structure JSON path (default: spm.json)",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Input workbook path. If omitted, auto-detect comments_sod_spm_tx.xlsx or comments_sod_spm_ts.xlsx.",
    )
    parser.add_argument(
        "--sheet",
        default="",
        help="Sheet name to use. If omitted, auto-detects a sheet with page columns.",
    )
    parser.add_argument(
        "--output",
        default="spm_structure.xlsx",
        help="Output workbook path (default: spm_structure.xlsx)",
    )
    return parser.parse_args()


def _load_json_object(json_path: Path) -> dict[str, Any]:
    raw = json_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"JSON file is empty: {json_path}")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Support fragment files that start with a key:value block instead of enclosing braces.
        parsed = json.loads("{" + raw + "}")

    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object at top level.")
    return parsed


def _extract_sections(spm_obj: dict[str, Any]) -> list[Section]:
    top_key, top_val = next(iter(spm_obj.items()))
    if not isinstance(top_val, dict) or "chapters" not in top_val:
        raise ValueError(f"Invalid structure under key {top_key!r}: missing chapters list.")

    chapters = top_val.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("chapters must be a list.")

    sections: list[Section] = []
    for ch in chapters:
        if not isinstance(ch, dict):
            continue
        number = str(ch.get("chapter_number", "")).strip()
        name = str(ch.get("chapter_name", "")).strip()
        from_page = pd.to_numeric(pd.Series([ch.get("from_page")]), errors="coerce").iloc[0]
        to_page = pd.to_numeric(pd.Series([ch.get("to_page")]), errors="coerce").iloc[0]

        if not number or pd.isna(from_page) or pd.isna(to_page):
            continue

        start = int(from_page)
        end = int(to_page)
        if start > end:
            start, end = end, start

        sections.append(
            Section(
                number=number,
                name=name,
                from_page=start,
                to_page=end,
            )
        )

    if not sections:
        raise ValueError("No usable section entries found in JSON chapters.")
    return sections


def _resolve_input_workbook(input_arg: str) -> Path:
    if input_arg:
        path = Path(input_arg)
        if not path.exists():
            raise FileNotFoundError(f"Input workbook not found: {path}")
        return path

    for candidate in [Path("comments_sod_spm_tx.xlsx"), Path("comments_sod_spm_ts.xlsx")]:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No default workbook found. Expected comments_sod_spm_tx.xlsx or comments_sod_spm_ts.xlsx."
    )


def _normalize_col_name(name: str) -> str:
    return str(name).strip().lower().replace("_", "")


def _choose_sheet(xls: pd.ExcelFile, sheet_arg: str) -> str:
    if sheet_arg:
        if sheet_arg not in xls.sheet_names:
            raise ValueError(f"Sheet not found: {sheet_arg}")
        return sheet_arg

    preferred = [s for s in xls.sheet_names if "spm" in s.lower() and "comment" in s.lower()]
    candidates = preferred if preferred else list(xls.sheet_names)

    for sheet in candidates:
        preview = pd.read_excel(xls, sheet_name=sheet, nrows=5)
        norm_cols = {_normalize_col_name(c) for c in preview.columns}
        if "frompage" in norm_cols and "topage" in norm_cols:
            return sheet

    raise ValueError("Could not auto-detect a sheet with Frompage/Topage columns.")


def _find_page_columns(df: pd.DataFrame) -> tuple[str, str]:
    normalized = {_normalize_col_name(c): str(c) for c in df.columns}
    from_col = normalized.get("frompage")
    to_col = normalized.get("topage")

    if not from_col or not to_col:
        raise KeyError("Input sheet must contain Frompage and Topage columns.")

    return from_col, to_col


def _match_sections(from_page: Any, to_page: Any, sections: list[Section]) -> tuple[str, str, int]:
    fp = pd.to_numeric(pd.Series([from_page]), errors="coerce").iloc[0]
    tp = pd.to_numeric(pd.Series([to_page]), errors="coerce").iloc[0]

    if pd.isna(fp) and pd.isna(tp):
        return "", "", 0

    if pd.isna(fp):
        fp = tp
    if pd.isna(tp):
        tp = fp

    start = int(fp)
    end = int(tp)
    if start > end:
        start, end = end, start

    # Business rule: full-document coverage should map to a single "full" section.
    if (start, end) in {(0, 16), (0, 15), (1, 16), (1, 15)}:
        return "full", "full", 1

    overlaps: list[Section] = []
    for sec in sections:
        overlap_start = max(start, sec.from_page)
        overlap_end = min(end, sec.to_page)
        if overlap_start <= overlap_end:
            overlaps.append(sec)

    if not overlaps:
        return "", "", 0

    numbers = " | ".join(sec.number for sec in overlaps)
    names = " | ".join(sec.name for sec in overlaps)
    return numbers, names, len(overlaps)


def build_spm_structure(json_path: Path, input_xlsx: Path, output_xlsx: Path, sheet_arg: str = "") -> Path:
    spm_obj = _load_json_object(json_path)
    sections = _extract_sections(spm_obj)

    xls = pd.ExcelFile(input_xlsx)
    sheet_name = _choose_sheet(xls, sheet_arg)
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)

    from_col, to_col = _find_page_columns(df)

    from_numeric = pd.to_numeric(df[from_col], errors="coerce")
    df = df[(from_numeric.isna()) | (from_numeric <= 16)].copy()

    matches = [
        _match_sections(row[from_col], row[to_col], sections)
        for _, row in df.iterrows()
    ]

    df_out = df.copy()
    df_out["SPM_Section_Number"] = [m[0] for m in matches]
    df_out["SPM_Section_Name"] = [m[1] for m in matches]
    df_out["SPM_Section_Match_Count"] = [m[2] for m in matches]

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_xlsx) as writer:
        df_out.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Input workbook: {input_xlsx}")
    print(f"Input sheet: {sheet_name}")
    print(f"Rows processed: {len(df_out)}")
    print(f"Output workbook: {output_xlsx}")
    return output_xlsx


def main() -> None:
    args = _parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    input_xlsx = _resolve_input_workbook(args.input)
    output_xlsx = Path(args.output)

    build_spm_structure(
        json_path=json_path,
        input_xlsx=input_xlsx,
        output_xlsx=output_xlsx,
        sheet_arg=args.sheet,
    )


if __name__ == "__main__":
    main()
