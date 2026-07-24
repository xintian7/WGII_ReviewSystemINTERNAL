#!/usr/bin/env python3
"""Unified affiliation type identification pipeline.

This script merges:
- 5-pass deterministic classification from analyze_affiliation.py
- GPT enrichment for remaining Unknown organizations from classify_unknown_affiliations_gpt.py

Default behavior:
- Reads encrypted parquet input
- Runs 5-pass classification
- Uses GPT only for unique organizations still Unknown
- Maps GPT results back to rows
- Writes one Excel output with row results and unknown-org mapping
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from cryptography.fernet import Fernet
from openai import AzureOpenAI, NotFoundError

try:
    from rapidfuzz import fuzz, process
except ImportError:
    process = None
    fuzz = None


DEFAULT_INPUT = "data/revcom.parquet.enc"
DEFAULT_OUTPUT = "affiliation_identified.xlsx"
DEFAULT_KEY_ENV = "FERNET_KEY"

DEFAULT_ORGANIZATION_LOOKUP = "lookup/organization_lookup.csv"
DEFAULT_ACRONYM_LOOKUP = "lookup/acronym_lookup.csv"
DEFAULT_ALIAS_LOOKUP = "lookup/alias_lookup.csv"

DEFAULT_AZURE_ENDPOINT = "https://azureopenaitsu.openai.azure.com/"
DEFAULT_DEPLOYMENT = "gpt-5.2"
DEFAULT_API_VERSION = "2024-12-01-preview"
DEFAULT_AZURE_KEY_ENV = "AZURE_API_KEY"
DEFAULT_LIMIT = 0

SECTOR_UNKNOWN = "Unknown"
SECTOR_INDEPENDENT = "Independent"
SECTOR_ACADEMIC = "Academic sector"
SECTOR_RESEARCH = "Research sector"
SECTOR_GOV = "Government & Intergovernmental sector"
SECTOR_CIVIL = "Civil society"
SECTOR_PRIVATE = "Private sector"

PASS_KEYS = ["p1", "p2", "p3", "p4", "p5"]
PASS_COLUMNS = ["res_p1", "res_p2", "res_p3", "res_p4", "res_p5"]

SECTOR_PRIORITY = {
    SECTOR_INDEPENDENT: 0,
    SECTOR_ACADEMIC: 1,
    SECTOR_RESEARCH: 2,
    SECTOR_GOV: 3,
    SECTOR_CIVIL: 4,
    SECTOR_PRIVATE: 5,
    SECTOR_UNKNOWN: 99,
}

ALLOWED_SECTORS = [
    SECTOR_INDEPENDENT,
    SECTOR_ACADEMIC,
    SECTOR_RESEARCH,
    SECTOR_GOV,
    SECTOR_CIVIL,
    SECTOR_PRIVATE,
]

KEYWORD_RULES: dict[str, list[str]] = {
    SECTOR_INDEPENDENT: [
        "independent researcher",
        "consultant",
        "freelance",
        "self-employed",
        "retired",
    ],
    SECTOR_ACADEMIC: [
        "university",
        "college",
        "polytechnic",
        "institute of technology",
        "school of",
        "faculty",
        "department of",
        "campus",
    ],
    SECTOR_RESEARCH: [
        "research institute",
        "institute",
        "laboratory",
        "lab",
        "observatory",
        "center for research",
        "academy of sciences",
        "iiasa",
        "cnrs",
        "csiro",
        "max planck",
        "helmholtz",
        "deltares",
        "tno",
        "inrae",
        "pik",
        "cmcc",
        "lsce",
        "ipsl",
        "cgiar",
        "cifor",
        "iwmi",
        "icimod",
        "ird",
    ],
    SECTOR_GOV: [
        "ministry",
        "department",
        "agency",
        "authority",
        "administration",
        "municipality",
        "city council",
        "bureau",
        "directorate",
        "commission",
        "united nations",
        "unep",
        "undp",
        "unesco",
        "wmo",
        "who",
        "fao",
        "oecd",
        "world bank",
        "asian development bank",
        "european commission",
        "european union",
        "ipcc technical support unit",
        "nasa",
        "noaa",
        "environment and climate change canada",
        "uk met office",
    ],
    SECTOR_CIVIL: [
        "foundation",
        "association",
        "society",
        "federation",
        "alliance",
        "network",
        "nonprofit",
        "non-profit",
        "world resources institute",
        "stockholm environment institute",
        "climate analytics",
        "future earth",
        "iclei",
        "c40",
        "conservation international",
        "global covenant of mayors",
    ],
    SECTOR_PRIVATE: [
        " ltd",
        " limited",
        " inc",
        " llc",
        " plc",
        " gmbh",
        " bv",
        " sas",
        " sa",
        " corporation",
        " company",
        " consulting",
        " advisors",
        " associates",
        "accenture",
        "arup",
        "erm",
        "microsoft research",
        "shell",
        "deloitte",
        "kpmg",
    ],
}

DEFAULT_ACRONYM_MAP: dict[str, dict[str, str]] = {
    "LSCE": {"canonical": "LSCE", "sector": SECTOR_RESEARCH},
    "IPSL": {"canonical": "IPSL", "sector": SECTOR_RESEARCH},
    "IIASA": {"canonical": "IIASA", "sector": SECTOR_RESEARCH},
    "WRI": {"canonical": "World Resources Institute", "sector": SECTOR_CIVIL},
    "SEI": {"canonical": "Stockholm Environment Institute", "sector": SECTOR_CIVIL},
    "UNDP": {"canonical": "UNDP", "sector": SECTOR_GOV},
    "UNEP": {"canonical": "UNEP", "sector": SECTOR_GOV},
    "UNESCO": {"canonical": "UNESCO", "sector": SECTOR_GOV},
    "WMO": {"canonical": "WMO", "sector": SECTOR_GOV},
    "WHO": {"canonical": "WHO", "sector": SECTOR_GOV},
    "FAO": {"canonical": "FAO", "sector": SECTOR_GOV},
    "OECD": {"canonical": "OECD", "sector": SECTOR_GOV},
    "NASA": {"canonical": "NASA", "sector": SECTOR_GOV},
    "NOAA": {"canonical": "NOAA", "sector": SECTOR_GOV},
    "WWF": {"canonical": "WWF", "sector": SECTOR_CIVIL},
    "MIT": {"canonical": "MIT", "sector": SECTOR_ACADEMIC},
    "EPFL": {"canonical": "EPFL", "sector": SECTOR_ACADEMIC},
    "NUS": {"canonical": "NUS", "sector": SECTOR_ACADEMIC},
    "NTU": {"canonical": "NTU", "sector": SECTOR_ACADEMIC},
    "HKU": {"canonical": "HKU", "sector": SECTOR_ACADEMIC},
    "KAUST": {"canonical": "KAUST", "sector": SECTOR_ACADEMIC},
    "IIT": {"canonical": "IIT", "sector": SECTOR_ACADEMIC},
    "IISC": {"canonical": "IISc", "sector": SECTOR_ACADEMIC},
    "NUST": {"canonical": "NUST", "sector": SECTOR_ACADEMIC},
}


@dataclass
class ClassificationResult:
    original: str
    cleaned: str
    canonical_name: str = ""
    sector: str = SECTOR_UNKNOWN
    subsector: str = ""
    method: str = ""
    confidence: float = 0.0
    organization_id: str = ""
    openalex_id: str = ""
    ror_id: str = ""


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


def _load_env_candidates(input_path: Path) -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        input_path.resolve().parent / ".env",
        input_path.resolve().parent.parent / ".env",
    ]

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        _load_env_file_if_present(candidate)


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


def load_lookup_csv(path: str | None, acronym_mode: bool = False) -> dict[str, dict[str, str]]:
    if path is None or not Path(path).exists():
        return {}

    df = pd.read_csv(path)
    required_cols = {"alias", "canonical", "sector"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Lookup file {path} missing columns: {sorted(missing)}")

    out: dict[str, dict[str, str]] = {}
    for _, r in df.iterrows():
        alias = str(r["alias"])
        key = re.sub(r"[^A-Za-z0-9]", "", alias).upper() if acronym_mode else alias.lower()
        out[key] = {
            "canonical": str(r["canonical"]),
            "sector": str(r["sector"]),
        }
    return out


def _find_id_column(columns: list[str]) -> str:
    lower_name_map = {c.lower(): c for c in columns}
    for candidate in ["commentsid", "commentid", "comment_id"]:
        if candidate in lower_name_map:
            return lower_name_map[candidate]
    raise KeyError("No comment id column found. Tried: commentsid, commentid, comment_id.")


class AffiliationClassifier:
    def __init__(
        self,
        organization_lookup: dict[str, dict[str, str]] | None = None,
        acronym_lookup: dict[str, dict[str, str]] | None = None,
        alias_lookup: dict[str, dict[str, str]] | None = None,
        keyword_rules: dict[str, list[str]] | None = None,
        fuzzy_threshold: int = 92,
    ) -> None:
        self.organization_lookup = organization_lookup or {}
        self.acronym_lookup = acronym_lookup or {}
        self.alias_lookup = alias_lookup or {}
        self.keyword_rules = keyword_rules or {}
        self.fuzzy_threshold = fuzzy_threshold

    def clean(self, text: str) -> str:
        text = text or ""
        text = text.replace("&", " and ")
        text = re.sub(r"[;,]+", ";", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def split_affiliations(self, text: str) -> list[str]:
        text = self.clean(text)
        return [
            x.strip()
            for x in re.split(r"\s*(?:;|/|\band\b)\s*", text, flags=re.IGNORECASE)
            if x.strip()
        ]

    def pass1_exact_lookup(self, org: str, result: ClassificationResult) -> ClassificationResult:
        key = org.lower()
        if key in self.organization_lookup:
            rec = self.organization_lookup[key]
            result.canonical_name = rec["canonical"]
            result.sector = rec["sector"]
            result.method = "ExactLookup"
            result.confidence = 1.0
        return result

    def pass2_acronym(self, org: str, result: ClassificationResult) -> ClassificationResult:
        token = re.sub(r"[^A-Za-z0-9]", "", org).upper()
        if token in self.acronym_lookup and result.confidence < 0.95:
            rec = self.acronym_lookup[token]
            result.canonical_name = rec["canonical"]
            result.sector = rec["sector"]
            result.method = "Acronym"
            result.confidence = 0.95
        return result

    def pass3_fuzzy(self, org: str, result: ClassificationResult) -> ClassificationResult:
        if process is None or fuzz is None:
            return result
        if result.confidence >= 0.95:
            return result
        if not self.alias_lookup:
            return result

        match = process.extractOne(org, list(self.alias_lookup.keys()), scorer=fuzz.WRatio)
        if match and match[1] >= self.fuzzy_threshold:
            rec = self.alias_lookup[match[0]]
            result.canonical_name = rec["canonical"]
            result.sector = rec["sector"]
            result.method = "FuzzyAlias"
            result.confidence = match[1] / 100.0
        return result

    def pass4_keywords(self, org: str, result: ClassificationResult) -> ClassificationResult:
        if result.confidence >= 0.80:
            return result

        txt = org.lower()

        if "state" in txt and "university" in txt:
            result.sector = SECTOR_ACADEMIC
            result.canonical_name = org
            result.method = "Keyword"
            result.confidence = 0.80
            return result

        for sector, words in self.keyword_rules.items():
            if any(word in txt for word in words):
                result.sector = sector
                result.canonical_name = org
                result.method = "Keyword"
                result.confidence = 0.80
                break
        return result

    def pass5_openalex(self, result: ClassificationResult) -> ClassificationResult:
        return result

    def _select_best_candidate(self, candidates: list[dict[str, object]]) -> dict[str, object]:
        known = [c for c in candidates if str(c.get("sector", SECTOR_UNKNOWN)) != SECTOR_UNKNOWN]
        if not known:
            return {
                "sector": SECTOR_UNKNOWN,
                "canonical_name": "",
                "method": "",
                "confidence": 0.0,
            }

        return max(
            known,
            key=lambda c: (
                float(c.get("confidence", 0.0)),
                -SECTOR_PRIORITY.get(str(c.get("sector", SECTOR_UNKNOWN)), 100),
            ),
        )

    def classify_org_with_trace(self, org: str) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
        res = ClassificationResult(original=org, cleaned=self.clean(org))
        pass_trace: dict[str, dict[str, object]] = {}

        res = self.pass1_exact_lookup(org, res)
        pass_trace["p1"] = {
            "sector": res.sector,
            "confidence": res.confidence,
            "method": res.method,
            "canonical_name": res.canonical_name,
        }

        res = self.pass2_acronym(org, res)
        pass_trace["p2"] = {
            "sector": res.sector,
            "confidence": res.confidence,
            "method": res.method,
            "canonical_name": res.canonical_name,
        }

        res = self.pass3_fuzzy(org, res)
        pass_trace["p3"] = {
            "sector": res.sector,
            "confidence": res.confidence,
            "method": res.method,
            "canonical_name": res.canonical_name,
        }

        res = self.pass4_keywords(org, res)
        pass_trace["p4"] = {
            "sector": res.sector,
            "confidence": res.confidence,
            "method": res.method,
            "canonical_name": res.canonical_name,
        }

        res = self.pass5_openalex(res)
        pass_trace["p5"] = {
            "sector": res.sector,
            "confidence": res.confidence,
            "method": res.method,
            "canonical_name": res.canonical_name,
        }

        return asdict(res), pass_trace

    def classify_affiliation_summary(self, affiliation: str) -> dict[str, object]:
        orgs = self.split_affiliations(affiliation)
        if not orgs:
            return {
                "res_p1": SECTOR_UNKNOWN,
                "res_p2": SECTOR_UNKNOWN,
                "res_p3": SECTOR_UNKNOWN,
                "res_p4": SECTOR_UNKNOWN,
                "res_p5": SECTOR_UNKNOWN,
                "primary_result": SECTOR_UNKNOWN,
                "primary_org": "",
                "primary_method": "",
                "primary_confidence": 0.0,
            }

        pass_candidates: dict[str, list[dict[str, object]]] = {k: [] for k in PASS_KEYS}
        final_candidates: list[dict[str, object]] = []

        for org in orgs:
            final_res, trace = self.classify_org_with_trace(org)
            final_candidates.append(final_res)
            for pass_key in PASS_KEYS:
                pass_candidates[pass_key].append(trace[pass_key])

        summary: dict[str, object] = {}
        for pass_key, pass_col in zip(PASS_KEYS, PASS_COLUMNS):
            best = self._select_best_candidate(pass_candidates[pass_key])
            summary[pass_col] = best["sector"]

        best_final = self._select_best_candidate(final_candidates)
        summary["primary_result"] = best_final["sector"]
        summary["primary_org"] = str(best_final.get("canonical_name", ""))
        summary["primary_method"] = str(best_final.get("method", ""))
        summary["primary_confidence"] = float(best_final.get("confidence", 0.0))
        return summary

    def classify(self, affiliation: str) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []

        for org in self.split_affiliations(affiliation):
            final_res, _ = self.classify_org_with_trace(org)
            records.append(final_res)

        if not records:
            records.append(
                asdict(
                    ClassificationResult(
                        original="",
                        cleaned="",
                        sector=SECTOR_UNKNOWN,
                        method="",
                        confidence=0.0,
                    )
                )
            )
        return records


def _clean_org_name(value: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_unknown_orgs_for_row(classifier: AffiliationClassifier, affiliation: str) -> list[str]:
    records = classifier.classify(affiliation)
    unknown_orgs: list[str] = []
    seen: set[str] = set()

    for rec in records:
        sector = str(rec.get("sector", SECTOR_UNKNOWN))
        if sector != SECTOR_UNKNOWN:
            continue

        org = _clean_org_name(str(rec.get("cleaned") or rec.get("original") or ""))
        if not org:
            continue

        key = org.lower()
        if key in seen:
            continue
        seen.add(key)
        unknown_orgs.append(org)

    return unknown_orgs


def _chunk_list(items: list[str], chunk_size: int) -> list[list[str]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _print_progress(current: int, total: int, label: str) -> None:
    print(f"{label}: {current}/{total}", end="\r", flush=True)
    if current >= total:
        print()


def _extract_json_payload(text: str) -> dict[str, Any]:
    candidate = (text or "").strip()
    if not candidate:
        return {}

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", candidate)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _classify_unknowns_with_gpt(
    client: AzureOpenAI,
    deployment: str,
    unknown_orgs: list[str],
    batch_size: int,
) -> dict[str, str]:
    if not unknown_orgs:
        return {}

    mapping: dict[str, str] = {}
    batches = _chunk_list(unknown_orgs, max(1, batch_size))

    system_prompt = (
        "You classify organization names into one predefined sector type. "
        "Return only JSON with this shape: "
        "{\"results\":[{\"organization\":\"...\",\"sector\":\"...\"}]}. "
        "Allowed sectors are exactly: " + ", ".join(ALLOWED_SECTORS) + ". "
        "If uncertain, choose the best sector from the allowed list; do not output Unknown."
    )

    total_batches = len(batches)
    for idx, batch in enumerate(batches, start=1):
        _print_progress(idx, total_batches, "GPT batches")
        user_prompt = {
            "allowed_sectors": ALLOWED_SECTORS,
            "organizations": batch,
        }

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=True)},
            ],
            temperature=0,
            max_completion_tokens=4000,
        )

        text = response.choices[0].message.content or ""
        payload = _extract_json_payload(text)
        results = payload.get("results", [])
        if not isinstance(results, list):
            continue

        for item in results:
            if not isinstance(item, dict):
                continue
            org = _clean_org_name(str(item.get("organization", "")))
            sector = str(item.get("sector", "")).strip()
            if not org:
                continue
            if sector not in ALLOWED_SECTORS:
                sector = SECTOR_UNKNOWN
            mapping[org.lower()] = sector

    return mapping


def _first_known_sector(sectors: list[str]) -> str:
    for sector in sectors:
        if sector and sector != SECTOR_UNKNOWN:
            return sector
    return SECTOR_UNKNOWN


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Identify affiliation type using 5-pass rules and optional GPT enrichment."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help=f"Encrypted parquet input (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Output Excel file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--key-env", default=DEFAULT_KEY_ENV, help=f"Fernet key env var (default: {DEFAULT_KEY_ENV})")
    parser.add_argument(
        "--organization-lookup",
        default=DEFAULT_ORGANIZATION_LOOKUP,
        help=f"CSV for exact organization lookup (default: {DEFAULT_ORGANIZATION_LOOKUP})",
    )
    parser.add_argument(
        "--acronym-lookup",
        default=DEFAULT_ACRONYM_LOOKUP,
        help=f"CSV for acronym lookup (default: {DEFAULT_ACRONYM_LOOKUP})",
    )
    parser.add_argument(
        "--alias-lookup",
        default=DEFAULT_ALIAS_LOOKUP,
        help=f"CSV for alias/fuzzy lookup (default: {DEFAULT_ALIAS_LOOKUP})",
    )
    parser.add_argument("--fuzzy-threshold", type=int, default=92, help="Fuzzy threshold (default: 92)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Rows for quick test. Use <=0 for all rows.")
    parser.add_argument("--disable-gpt", action="store_true", help="Skip GPT enrichment and keep only 5-pass output")
    parser.add_argument("--api-version", default=DEFAULT_API_VERSION, help=f"Azure API version (default: {DEFAULT_API_VERSION})")
    parser.add_argument("--azure-key-env", default=DEFAULT_AZURE_KEY_ENV, help="Environment variable containing Azure OpenAI API key")
    parser.add_argument("--batch-size", type=int, default=20, help="Unknown organizations per GPT request")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    _load_env_candidates(input_path)

    df = decrypt_parquet_to_dataframe(input_path, args.key_env)
    lower_name_map = {c.lower(): c for c in df.columns}
    if "affiliation" not in lower_name_map:
        raise KeyError("Column 'affiliation' was not found in decrypted dataset.")

    id_col = _find_id_column(list(df.columns))
    affiliation_col = lower_name_map["affiliation"]

    result = pd.DataFrame(
        {
            "commentsid": df[id_col],
            "affiliation": df[affiliation_col].fillna("").astype(str),
        }
    )

    if args.limit > 0:
        result = result.head(args.limit).copy()

    organization_lookup = load_lookup_csv(args.organization_lookup)
    acronym_lookup = {**DEFAULT_ACRONYM_MAP, **load_lookup_csv(args.acronym_lookup, acronym_mode=True)}
    alias_lookup = load_lookup_csv(args.alias_lookup)

    classifier = AffiliationClassifier(
        organization_lookup=organization_lookup,
        acronym_lookup=acronym_lookup,
        alias_lookup=alias_lookup,
        keyword_rules=KEYWORD_RULES,
        fuzzy_threshold=args.fuzzy_threshold,
    )

    summary_payloads: list[dict[str, object]] = []
    total_rows = len(result)
    for idx, affiliation in enumerate(result["affiliation"].tolist(), start=1):
        _print_progress(idx, total_rows, "5-pass summary")
        summary_payloads.append(classifier.classify_affiliation_summary(affiliation))

    summary_results = pd.Series(summary_payloads, index=result.index)
    summary_df = pd.DataFrame(summary_results.tolist(), index=result.index)
    result = pd.concat([result, summary_df], axis=1)

    unknown_orgs_payload: list[list[str]] = []
    for idx, affiliation in enumerate(result["affiliation"].tolist(), start=1):
        _print_progress(idx, total_rows, "Extract unknown orgs")
        unknown_orgs_payload.append(_extract_unknown_orgs_for_row(classifier, affiliation))
    result["unknown_orgs"] = pd.Series(unknown_orgs_payload, index=result.index)

    unique_unknown_orgs = sorted(
        {
            org
            for orgs in result["unknown_orgs"].tolist()
            for org in orgs
            if org
        }
    )

    gpt_mapping: dict[str, str] = {}
    if not args.disable_gpt and unique_unknown_orgs:
        api_key = os.getenv(args.azure_key_env, "").strip()
        if not api_key:
            raise RuntimeError(f"Missing Azure OpenAI API key in environment variable: {args.azure_key_env}")

        client = AzureOpenAI(
            api_version=args.api_version,
            azure_endpoint=DEFAULT_AZURE_ENDPOINT,
            api_key=api_key,
        )

        try:
            gpt_mapping = _classify_unknowns_with_gpt(
                client=client,
                deployment=DEFAULT_DEPLOYMENT,
                unknown_orgs=unique_unknown_orgs,
                batch_size=args.batch_size,
            )
        except NotFoundError as exc:
            raise RuntimeError(
                "Azure deployment configured in code was not found. "
                f"Current deployment is '{DEFAULT_DEPLOYMENT}'. "
                "Update DEFAULT_DEPLOYMENT in this script to a valid deployment name."
            ) from exc

    gpt_unknown_types: list[list[str]] = []
    primary_after_gpt: list[str] = []
    for idx, (_, row) in enumerate(result.iterrows(), start=1):
        _print_progress(idx, total_rows, "Map GPT to rows")
        row_types = [gpt_mapping.get(org.lower(), SECTOR_UNKNOWN) for org in row["unknown_orgs"]]
        gpt_unknown_types.append(row_types)
        if row["primary_result"] != SECTOR_UNKNOWN:
            primary_after_gpt.append(str(row["primary_result"]))
        else:
            primary_after_gpt.append(_first_known_sector(row_types))

    result["gpt_unknown_types"] = pd.Series(gpt_unknown_types, index=result.index)
    result["primary_result_after_gpt"] = pd.Series(primary_after_gpt, index=result.index)

    mapping_df = pd.DataFrame(
        {
            "unknown_organization": unique_unknown_orgs,
            "gpt_sector": [gpt_mapping.get(org.lower(), SECTOR_UNKNOWN) for org in unique_unknown_orgs],
        }
    )

    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        result.to_excel(writer, index=False, sheet_name="affiliations")
        mapping_df.to_excel(writer, index=False, sheet_name="unknown_org_mapping")

    print(f"Saved: {args.output}")
    print(f"Rows processed: {len(result)}")
    print(f"Unique unknown orgs: {len(unique_unknown_orgs)}")
    print(f"GPT enabled: {not args.disable_gpt}")


if __name__ == "__main__":
    main()
