"""
BH3 - Metadata extraction (policy id, version, effective date, control id, ...).

Reads the BH2 parsed JSON for a document, pulls the key/value "info box" table
that appears at the top of every policy / work-paper page 1 (POLICY ID,
VERSION, STATUS, EFFECTIVE, CONTROL ID, ... or WORK PAPER ID, AUDIT CYCLE, ...)
and normalizes it into a flat, typed metadata record.

A second pass (`link_versions`) reconciles metadata *across* documents that
share the same policy_id, so each version knows what it supersedes / is
superseded by and which one is currently in force — this is what BH7's
"version-in-force filter" will key off of.
"""

from __future__ import annotations

import re
from typing import Any

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# maps the raw label text found in the info-box table to a normalized field name
LABEL_MAP = {
    "POLICY ID": "policy_id",
    "WORK PAPER ID": "work_paper_id",
    "VERSION": "version",
    "STATUS": "status_raw",
    "EFFECTIVE": "effective_date_raw",
    "SUPERSEDED": "superseded_date_raw",
    "CONTROL ID": "control_id",
    "PROCESS AREA": "process_area",
    "OWNER": "owner",
    "CHANGE BASIS": "change_basis",
    "PROGRAM": "change_basis",
    "AUDIT CYCLE": "audit_cycle",
    "DATE PREPARED": "date_prepared_raw",
    "POLICY TESTED": "policy_tested_raw",
    "PREPARED BY": "prepared_by",
}


def parse_month_year(text: str | None) -> str | None:
    """'January 2025' -> '2025-01'. Returns None if it can't be parsed."""
    if not text:
        return None
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", text)
    if not m:
        return None
    month = MONTHS.get(m.group(1).strip().lower())
    if not month:
        return None
    return f"{m.group(2)}-{month:02d}"


def parse_policy_ref(text: str | None) -> dict[str, str | None]:
    """'POL-ORD-001 v1.0' -> {'policy_id': 'POL-ORD-001', 'version': '1.0'}"""
    if not text:
        return {"policy_id": None, "version": None}
    m = re.search(r"(POL-ORD-\d+)\s*v?([\d.]+)", text, re.IGNORECASE)
    if not m:
        return {"policy_id": None, "version": None}
    return {"policy_id": m.group(1).upper(), "version": m.group(2)}


def _find_info_table(parsed_doc: dict[str, Any]) -> list[list[str]] | None:
    """The info-box table is always the first table block in the document."""
    for page in parsed_doc.get("pages", []):
        for block in page.get("blocks", []):
            if block.get("block_type") == "table":
                return block.get("rows") or []
    return None


def _flatten_info_table(rows: list[list[str]]) -> dict[str, str]:
    """Each row is [label, value, label, value] (2 key/value pairs per row)."""
    raw: dict[str, str] = {}
    for row in rows:
        for i in range(0, len(row) - 1, 2):
            label, value = (row[i] or "").strip(), (row[i + 1] or "").strip()
            if label and value:
                raw[label.upper()] = value
    return raw


def extract_metadata(parsed_doc: dict[str, Any], parsed_json_path: str) -> dict[str, Any]:
    table_rows = _find_info_table(parsed_doc)
    if not table_rows:
        return {
            "doc_id": None,
            "doc_type": "unknown",
            "parse_error": "no info-box table found on page 1",
            "parsed_json_path": parsed_json_path,
            "source_file": parsed_doc.get("source_file"),
        }

    raw = _flatten_info_table(table_rows)
    fields = {LABEL_MAP[k]: v for k, v in raw.items() if k in LABEL_MAP}

    doc_type = "policy" if "policy_id" in fields else "work_paper" if "work_paper_id" in fields else "unknown"

    status_raw = fields.get("status_raw", "")
    if status_raw.upper().startswith("ACTIVE"):
        status = "ACTIVE"
    elif status_raw.upper().startswith("SUPERSEDED"):
        status = "SUPERSEDED"
    elif status_raw.upper().startswith("CLOSED"):
        status = "CLOSED"
    else:
        status = status_raw.upper() or None

    # work papers embed their superseded date inline in status_raw, e.g.
    # "CLOSED — superseded Jan 2025"
    superseded_date = parse_month_year(fields.get("superseded_date_raw")) or parse_month_year(status_raw)

    policy_tested = parse_policy_ref(fields.get("policy_tested_raw"))

    meta: dict[str, Any] = {
        "doc_type": doc_type,
        "policy_id": fields.get("policy_id") or fields.get("work_paper_id"),
        "version": fields.get("version"),
        "status": status,
        "effective_date": parse_month_year(fields.get("effective_date_raw")),
        "superseded_date": superseded_date,
        "control_id": fields.get("control_id"),
        "process_area": fields.get("process_area"),
        "owner": fields.get("owner"),
        "change_basis": fields.get("change_basis"),
        "audit_cycle": fields.get("audit_cycle"),
        "date_prepared": parse_month_year(fields.get("date_prepared_raw")),
        "prepared_by": fields.get("prepared_by"),
        "tests_policy_id": policy_tested["policy_id"],
        "tests_policy_version": policy_tested["version"],
        "source_file": parsed_doc.get("source_file"),
        "parsed_json_path": parsed_json_path,
    }

    if doc_type == "policy":
        meta["doc_id"] = f"{meta['policy_id']}_v{meta['version']}"
    elif doc_type == "work_paper":
        meta["doc_id"] = meta["policy_id"]
    else:
        meta["doc_id"] = None

    return meta


def link_versions(all_metadata: list[dict[str, Any]]) -> list[str]:
    """
    Cross-document reconciliation for same-policy_id records: fills in
    supersedes / superseded_by / is_current. Returns a list of human-readable
    data-quality warnings (e.g. two ACTIVE versions of the same policy).
    """
    warnings: list[str] = []
    by_policy: dict[str, list[dict[str, Any]]] = {}
    for m in all_metadata:
        if m["doc_type"] == "policy" and m.get("policy_id"):
            by_policy.setdefault(m["policy_id"], []).append(m)

    for policy_id, docs in by_policy.items():
        docs.sort(key=lambda d: float(d["version"] or 0))
        active_count = sum(1 for d in docs if d["status"] == "ACTIVE")
        if active_count != 1:
            warnings.append(f"{policy_id}: expected exactly 1 ACTIVE version, found {active_count}")

        for i, d in enumerate(docs):
            d["supersedes"] = docs[i - 1]["doc_id"] if i > 0 else None
            d["superseded_by"] = docs[i + 1]["doc_id"] if i < len(docs) - 1 else None
            d["is_current"] = d["status"] == "ACTIVE"
            if i < len(docs) - 1 and d["status"] != "SUPERSEDED":
                warnings.append(f"{d['doc_id']}: has a newer version but status is '{d['status']}', not SUPERSEDED")

    # cross-reference: does each work paper's tested policy+version actually exist?
    policy_doc_ids = {d["doc_id"] for d in all_metadata if d["doc_type"] == "policy"}
    for m in all_metadata:
        if m["doc_type"] == "work_paper" and m.get("tests_policy_id"):
            ref = f"{m['tests_policy_id']}_v{m['tests_policy_version']}"
            m["tests_policy_doc_id"] = ref if ref in policy_doc_ids else None
            if m["tests_policy_doc_id"] is None:
                warnings.append(f"{m['doc_id']}: cites '{ref}' which was not found among parsed policies")

    return warnings
