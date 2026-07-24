#!/usr/bin/env python3
"""Convert an Excel file to Parquet bytes and encrypt with a Fernet key from env.

Default behavior:
- Input: comments_taxonomy_classification.xlsx
- Output: comments_taxonomy_classification.parquet.enc
- Fernet key env var: FERNET_KEY

This script optionally reads a local .env file in the current working directory
if the key is not already available in process environment variables.
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


DEFAULT_INPUT = "comments_taxonomy_classification.xlsx"
DEFAULT_OUTPUT = "comments_taxonomy_classification.parquet.enc"
DEFAULT_KEY_ENV = "FERNET_KEY"


def _build_fernet_from_env_value(raw_key: str) -> Fernet:
    """Build Fernet from env value.

    - If raw_key is already a valid Fernet key, use it directly.
    - Otherwise, deterministically derive a valid Fernet key from the raw text.
    """
    raw_key = (raw_key or "").strip()
    if not raw_key:
        raise ValueError("Empty key value.")

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        derived_key = base64.urlsafe_b64encode(digest)
        return Fernet(derived_key)


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


def convert_and_encrypt_excel_to_parquet(
    input_excel: Path,
    output_enc: Path,
    key_env_var: str,
    compression: str,
    force: bool,
) -> Path:
    """Read Excel, serialize to Parquet bytes, encrypt with Fernet, and write .enc."""
    if not input_excel.exists() or not input_excel.is_file():
        raise FileNotFoundError(f"Input file not found: {input_excel}")

    if output_enc.exists() and not force:
        raise FileExistsError(
            f"Output file already exists: {output_enc}. Use --force to overwrite."
        )

    key = os.getenv(key_env_var, "").strip()
    if not key:
        raise RuntimeError(
            f"Missing Fernet key in environment variable: {key_env_var}"
        )

    # Accept either a true Fernet key or a passphrase-style env value.
    fernet = _build_fernet_from_env_value(key)

    df = pd.read_excel(input_excel)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, compression=compression)
    parquet_bytes = parquet_buffer.getvalue()

    encrypted_bytes = fernet.encrypt(parquet_bytes)

    output_enc.parent.mkdir(parents=True, exist_ok=True)
    output_enc.write_bytes(encrypted_bytes)

    return output_enc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Excel to Parquet and encrypt output with Fernet key from env."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Input Excel file path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output encrypted file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--key-env",
        default=DEFAULT_KEY_ENV,
        help=f"Environment variable name for Fernet key (default: {DEFAULT_KEY_ENV})",
    )
    parser.add_argument(
        "--compression",
        default="zstd",
        choices=["zstd", "snappy", "gzip", "brotli", "lz4", "none"],
        help="Parquet compression codec",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output if it already exists",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Best effort: load local .env if the key is not already exported.
    if not os.getenv(args.key_env):
        _load_env_file_if_present(Path(".env"))

    input_path = Path(args.input)
    output_path = Path(args.output)

    compression = None if args.compression == "none" else args.compression

    written = convert_and_encrypt_excel_to_parquet(
        input_excel=input_path,
        output_enc=output_path,
        key_env_var=args.key_env,
        compression=compression,
        force=args.force,
    )

    print(f"Encrypted parquet written to: {written}")


if __name__ == "__main__":
    main()
