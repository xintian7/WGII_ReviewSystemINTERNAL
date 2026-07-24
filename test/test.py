#!/usr/bin/env python3
"""Decrypt an encrypted parquet file and print the first 5 rows."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import os
from pathlib import Path

import pandas as pd
from cryptography.fernet import Fernet


DEFAULT_INPUT = "comments_taxonomy_classification.parquet.enc"
DEFAULT_KEY_ENV = "FERNET_KEY"


def _load_env_file_if_present(env_path: Path) -> None:
    """Load simple KEY=VALUE lines from .env into os.environ (without override)."""
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
    """Build Fernet from env key value or derive one from passphrase text."""
    raw_key = (raw_key or "").strip()
    if not raw_key:
        raise ValueError("Empty key value.")

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        derived_key = base64.urlsafe_b64encode(digest)
        return Fernet(derived_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decrypt encrypted parquet and print the first 5 rows."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Encrypted parquet file path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--key-env",
        default=DEFAULT_KEY_ENV,
        help=f"Environment variable name for key (default: {DEFAULT_KEY_ENV})",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=5,
        help="Number of rows to show (default: 5)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.getenv(args.key_env):
        _load_env_file_if_present(Path(".env"))

    key = os.getenv(args.key_env, "").strip()
    if not key:
        raise RuntimeError(f"Missing key in environment variable: {args.key_env}")

    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Encrypted file not found: {input_path}")

    fernet = _build_fernet_from_env_value(key)
    encrypted_bytes = input_path.read_bytes()
    parquet_bytes = fernet.decrypt(encrypted_bytes)

    df = pd.read_parquet(io.BytesIO(parquet_bytes))

    preview = df.head(max(0, args.rows)).copy()
    for col in preview.select_dtypes(include=["object", "str"]).columns:
        preview[col] = (
            preview[col]
            .fillna("")
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    print(f"Decrypted rows: {len(df)} | Columns: {len(df.columns)}")
    print(preview.to_string(index=False, max_colwidth=80))


if __name__ == "__main__":
    main()
