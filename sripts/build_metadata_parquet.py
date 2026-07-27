#!/usr/bin/env python3
"""Merge decrypted revcom data with affiliation results and re-encrypt as parquet.

Default input:
- data/revcom.parquet.enc
- affiliation_identified.xlsx

Default output:
- metadata.parquet.enc
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import os
from pathlib import Path

import pandas as pd
from cryptography.fernet import Fernet


DEFAULT_REVCOM_INPUT = "data/revcom.parquet.enc"
DEFAULT_AFFILIATION_INPUT = "data/affiliation_identified.xlsx"
DEFAULT_SRCITIES_INPUT = "srcities.csv"
DEFAULT_OUTPUT = "metadata.parquet.enc"
DEFAULT_KEY_ENV = "FERNET_KEY"


def _load_env_file_if_present(env_path: Path) -> None:
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
        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value


def _build_fernet_from_env_value(raw_key: str) -> Fernet:
    raw_key = (raw_key or "").strip()
    if not raw_key:
        raise ValueError("Empty key value.")

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        derived_key = base64.urlsafe_b64encode(digest)
        return Fernet(derived_key)


def decrypt_parquet_to_dataframe(input_enc: Path, key_env_var: str) -> pd.DataFrame:
    key = os.getenv(key_env_var, "").strip()
    if not key:
        raise RuntimeError(f"Missing key in environment variable: {key_env_var}")

    if not input_enc.exists() or not input_enc.is_file():
        raise FileNotFoundError(f"Encrypted file not found: {input_enc}")

    fernet = _build_fernet_from_env_value(key)
    encrypted_bytes = input_enc.read_bytes()
    parquet_bytes = fernet.decrypt(encrypted_bytes)
    return pd.read_parquet(io.BytesIO(parquet_bytes))


def encrypt_dataframe_to_parquet(df: pd.DataFrame, output_enc: Path, key_env_var: str) -> Path:
    key = os.getenv(key_env_var, "").strip()
    if not key:
        raise RuntimeError(f"Missing key in environment variable: {key_env_var}")

    fernet = _build_fernet_from_env_value(key)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, compression="zstd")
    encrypted_bytes = fernet.encrypt(parquet_buffer.getvalue())

    output_enc.parent.mkdir(parents=True, exist_ok=True)
    output_enc.write_bytes(encrypted_bytes)
    return output_enc


def _find_id_column(columns: list[str]) -> str:
    lower_name_map = {c.lower(): c for c in columns}
    for candidate in ["commentsid", "commentid", "comment_id"]:
        if candidate in lower_name_map:
            return lower_name_map[candidate]
    raise KeyError("No comment id column found. Tried: commentsid, commentid, comment_id.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge revcom.parquet.enc, affiliation_identified.xlsx, and srcities.csv into encrypted metadata.parquet.enc"
    )
    parser.add_argument("--revcom-input", default=DEFAULT_REVCOM_INPUT, help=f"Encrypted parquet input (default: {DEFAULT_REVCOM_INPUT})")
    parser.add_argument("--affiliation-input", default=DEFAULT_AFFILIATION_INPUT, help=f"Affiliation Excel input (default: {DEFAULT_AFFILIATION_INPUT})")
    parser.add_argument("--srcities-input", default=DEFAULT_SRCITIES_INPUT, help=f"SRCities CSV input (default: {DEFAULT_SRCITIES_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Encrypted output file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--key-env", default=DEFAULT_KEY_ENV, help=f"Fernet key env var (default: {DEFAULT_KEY_ENV})")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.getenv(args.key_env):
        _load_env_file_if_present(Path(".env"))

    revcom_df = decrypt_parquet_to_dataframe(Path(args.revcom_input), args.key_env)
    affiliation_df = pd.read_excel(Path(args.affiliation_input))
    srcities_df = pd.read_csv(Path(args.srcities_input))

    revcom_id = _find_id_column(list(revcom_df.columns))
    affiliation_id = _find_id_column(list(affiliation_df.columns))

    revcom_lower = {c.lower(): c for c in revcom_df.columns}
    aff_lower = {c.lower(): c for c in affiliation_df.columns}

    # Avoid duplicate columns by keeping only affiliation-derived extras.
    cols_to_append = [
        c for c in affiliation_df.columns
        if c.lower() not in {affiliation_id.lower(), "affiliation"}
    ]

    if "affiliation" in revcom_lower and "affiliation" in aff_lower:
        left_key_aff = revcom_lower["affiliation"]
        right_key_aff = aff_lower["affiliation"]
        aff_subset = affiliation_df[[affiliation_id, right_key_aff, *cols_to_append]].copy()
        aff_subset[right_key_aff] = aff_subset[right_key_aff].fillna("").astype(str)
        revcom_df[left_key_aff] = revcom_df[left_key_aff].fillna("").astype(str)

        merged = revcom_df.merge(
            aff_subset,
            how="left",
            left_on=[revcom_id, left_key_aff],
            right_on=[affiliation_id, right_key_aff],
            suffixes=("", "_aff"),
        )
        drop_cols = [c for c in [affiliation_id, right_key_aff] if c in merged.columns and c not in revcom_df.columns]
        if drop_cols:
            merged = merged.drop(columns=drop_cols)
    else:
        aff_subset = affiliation_df[[affiliation_id, *cols_to_append]].copy()
        merged = revcom_df.merge(
            aff_subset,
            how="left",
            left_on=revcom_id,
            right_on=affiliation_id,
            suffixes=("", "_aff"),
        )
        if affiliation_id in merged.columns and affiliation_id not in revcom_df.columns:
            merged = merged.drop(columns=[affiliation_id])

    srcities_id = _find_id_column(list(srcities_df.columns))
    srcities_isfp_col = None
    for col in srcities_df.columns:
        normalized = col.strip().lower()
        if normalized == "isfp" or normalized.startswith("isfp") or "isfp" in normalized:
            srcities_isfp_col = col
            break
    if not srcities_isfp_col:
        raise KeyError("No isfp column found in srcities input.")
    merged = merged.merge(
        srcities_df[[srcities_id, srcities_isfp_col]].rename(columns={srcities_isfp_col: "isfp"}),
        how="left",
        left_on=revcom_id,
        right_on=srcities_id,
    )
    if srcities_id in merged.columns and srcities_id != revcom_id:
        merged = merged.drop(columns=[srcities_id])

    out_path = encrypt_dataframe_to_parquet(merged, Path(args.output), args.key_env)

    print(f"Merged rows: {len(merged)}")
    print(f"Merged columns: {len(merged.columns)}")
    print(f"Saved encrypted metadata: {out_path}")


if __name__ == "__main__":
    main()
