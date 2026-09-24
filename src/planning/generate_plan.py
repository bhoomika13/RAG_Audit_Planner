"""
BH8 - Audit plan generation (deterministic, evidence-grounded).

Cross-references each ACTIVE policy version (BH3/BH4 metadata) against the
prior work paper that tested an earlier version of the same policy family
(via tests_policy_id / tests_policy_version / tests_policy_doc_id), pulls
forward open high-risk KRIs, exception findings and prior-period
recommendations from the BH5 chunks, and produces one planned audit item per
policy.

No LLM call — this stage is 100% deterministic and grounded directly in BH3
metadata + BH5 chunk data, so every planned item cites the exact chunk_id(s)
it was derived from.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

KRI_HEADER = ["KRI ID", "KRI Description", "Related Policy Clause", "Risk Rating"]
FINDINGS_HEADER = ["Step #", "Sample Size", "Exceptions Noted", "Exception Rate"]


@dataclass
class PlanItem:
    policy_id: str
    active_doc_id: str
    active_version: str
    control_id: str | None
    process_area: str | None
    owner: str | None
    prior_work_doc_id: str | None
    prior_tested_version: str | None
    prior_audit_cycle: str | None
    version_gap: bool
    priority: str
    objective: str
    open_high_risk_kris: list[dict[str, str]] = field(default_factory=list)
    exception_findings: list[dict[str, str]] = field(default_factory=list)
    carried_forward_recommendations: list[str] = field(default_factory=list)
    evidence_chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find_table(chunks: list[dict], doc_id: str, header: list[str]) -> tuple[list[list[str]], str | None]:
    """Locates the one table chunk for `doc_id` whose header row matches `header`, returns (data_rows, chunk_id)."""
    for c in chunks:
        m = c["metadata"]
        if m.get("doc_id") != doc_id or m.get("chunk_type") != "table":
            continue
        rows = m.get("table_rows") or []
        if rows and rows[0] == header:
            return rows[1:], m["chunk_id"]
    return [], None


def _find_recommendations(chunks: list[dict], doc_id: str) -> tuple[list[str], str | None]:
    """Pulls the bullet lines under "Prior Period Recommendations" for `doc_id`."""
    for c in chunks:
        m = c["metadata"]
        if m.get("doc_id") != doc_id or m.get("chunk_type") != "text":
            continue
        if "Prior Period Recommendations" not in c["page_content"]:
            continue
        recs = [line.lstrip("- ").strip() for line in c["page_content"].splitlines() if line.strip().startswith("-")]
        return recs, m["chunk_id"]
    return [], None


def build_audit_plan(metadata_index: list[dict], chunks: list[dict]) -> list[PlanItem]:
    policies = [m for m in metadata_index if m.get("doc_type") == "policy"]
    work_papers = [m for m in metadata_index if m.get("doc_type") == "work_paper"]
    active_policies = [p for p in policies if p.get("is_current")]

    items: list[PlanItem] = []
    for policy in active_policies:
        policy_id = policy["policy_id"]
        related_wps = [wp for wp in work_papers if wp.get("tests_policy_id") == policy_id]
        related_wps.sort(key=lambda wp: wp.get("date_prepared") or "", reverse=True)
        prior_wp = related_wps[0] if related_wps else None

        evidence_ids: list[str] = []
        high_kris: list[dict[str, str]] = []
        exceptions: list[dict[str, str]] = []
        recs: list[str] = []
        version_gap = False

        if prior_wp:
            version_gap = prior_wp.get("tests_policy_version") != policy.get("version")

            kri_rows, kri_chunk_id = _find_table(chunks, prior_wp["doc_id"], KRI_HEADER)
            high_kris = [{"kri_id": r[0], "description": r[1], "clause": r[2]} for r in kri_rows if r[3].strip().lower() == "high"]
            if kri_chunk_id:
                evidence_ids.append(kri_chunk_id)

            findings_rows, findings_chunk_id = _find_table(chunks, prior_wp["doc_id"], FINDINGS_HEADER)
            for row in findings_rows:
                rate_val = float(row[3].replace("%", "").strip() or 0)
                if rate_val > 0:
                    exceptions.append({"step": row[0], "sample_size": row[1], "exceptions": row[2], "rate": row[3]})
            if findings_chunk_id:
                evidence_ids.append(findings_chunk_id)

            recs, recs_chunk_id = _find_recommendations(chunks, prior_wp["doc_id"])
            if recs_chunk_id:
                evidence_ids.append(recs_chunk_id)

        priority = "High" if (not prior_wp or version_gap or high_kris) else "Medium"

        if not prior_wp:
            objective = (
                f"No prior audit coverage on record for {policy_id}. Perform a baseline test of "
                f"{policy['doc_id']} controls (control {policy.get('control_id')})."
            )
        elif version_gap:
            objective = (
                f"Policy changed since last audit (tested v{prior_wp['tests_policy_version']} -> now v{policy['version']}). "
                f"Re-baseline testing against {policy['doc_id']} and re-assess prior high-risk KRIs."
            )
        else:
            objective = f"Re-test {policy['doc_id']} controls (control {policy.get('control_id')}) per the standard audit cycle."

        items.append(PlanItem(
            policy_id=policy_id,
            active_doc_id=policy["doc_id"],
            active_version=policy["version"],
            control_id=policy.get("control_id"),
            process_area=policy.get("process_area"),
            owner=policy.get("owner"),
            prior_work_doc_id=prior_wp["doc_id"] if prior_wp else None,
            prior_tested_version=prior_wp.get("tests_policy_version") if prior_wp else None,
            prior_audit_cycle=prior_wp.get("audit_cycle") if prior_wp else None,
            version_gap=version_gap,
            priority=priority,
            objective=objective,
            open_high_risk_kris=high_kris,
            exception_findings=exceptions,
            carried_forward_recommendations=recs,
            evidence_chunk_ids=evidence_ids,
        ))

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    items.sort(key=lambda it: (priority_rank.get(it.priority, 1), it.policy_id))
    return items
