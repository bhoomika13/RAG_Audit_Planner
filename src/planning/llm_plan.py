"""
BH8 (LLM) - GPT-4.1 powered audit plan generation.

Builds a grounded context package (benchmark policy, prior work papers found,
the legacy audit-step checklist, carried-forward KRIs/exceptions/
recommendations - all extracted deterministically from BH3 metadata + BH5
chunks) and asks GPT-4.1 (Azure OpenAI) to produce a step-by-step audit plan,
classifying each step as new / updated / kept / dropped relative to the
legacy checklist, with a reason grounded in the supplied evidence.

The LLM is NOT given free rein over facts: KRIs, findings, recommendations
and the legacy steps are all extracted with the same deterministic table
parsing used in generate_plan.py, then handed to the model as structured
JSON context. The model's job is to reason about and phrase the plan, not to
invent evidence.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from planning.generate_plan import FINDINGS_HEADER, KRI_HEADER, _find_recommendations, _find_table
from planning.llm_config import get_llm

STEPS_HEADER = ["Step #", "Audit Step Description", "Policy Clause Tested", "Related KRI"]

SYSTEM_PROMPT = """You are an internal audit planning assistant.
You are given:
- a benchmark policy (the current, active policy version to audit against)
- the prior work papers found for that policy family
- the legacy audit-step checklist from the most recent prior work paper
- carried-forward high-risk KRIs, prior exceptions, and prior-period recommendations

Your task: produce an updated audit-step checklist for the next audit cycle.
For every step, decide one status relative to the legacy checklist:
- "new": a step not in the legacy checklist, needed because of a policy change, a KRI, or a prior finding
- "kept": a legacy step that is unchanged and still applies
- "updated": a legacy step whose scope/wording must change (e.g. policy clause renumbered, threshold changed)
- "dropped": a legacy step that is no longer needed (e.g. superseded by another step, already fully covered)

Rules:
- Ground every step in the provided context only. Do not invent facts, clause numbers, or KRIs not given to you.
- Every step must have a short "reason" explaining why it has that status, citing the specific policy clause, KRI id, or prior finding it is based on.
- Output ONLY valid JSON, matching this schema, with no markdown fences and no extra commentary:

{
  "audit_steps": [
    {"status": "new|kept|updated|dropped", "description": "string", "reason": "string"}
  ]
}
"""


def _gather_context(policy_id: str, metadata_index: list[dict], chunks: list[dict]) -> dict[str, Any]:
    policies = [m for m in metadata_index if m.get("doc_type") == "policy" and m.get("policy_id") == policy_id]
    work_papers = [m for m in metadata_index if m.get("doc_type") == "work_paper" and m.get("tests_policy_id") == policy_id]

    benchmark = next((p for p in policies if p.get("is_current")), None)
    if benchmark is None:
        raise ValueError(f"No active/current policy found for policy_id={policy_id!r}")

    work_papers.sort(key=lambda wp: wp.get("date_prepared") or "", reverse=True)
    most_recent_wp = work_papers[0] if work_papers else None

    legacy_steps: list[dict[str, str]] = []
    if most_recent_wp:
        step_rows, _ = _find_table(chunks, most_recent_wp["doc_id"], STEPS_HEADER)
        legacy_steps = [
            {"step": r[0], "description": r[1], "clause": r[2], "kri": r[3]}
            for r in step_rows
        ]

    high_kris: list[dict[str, str]] = []
    exceptions: list[dict[str, str]] = []
    recommendations: list[str] = []
    if most_recent_wp:
        kri_rows, _ = _find_table(chunks, most_recent_wp["doc_id"], KRI_HEADER)
        high_kris = [{"kri_id": r[0], "description": r[1], "clause": r[2]} for r in kri_rows if r[3].strip().lower() == "high"]

        findings_rows, _ = _find_table(chunks, most_recent_wp["doc_id"], FINDINGS_HEADER)
        for row in findings_rows:
            rate_val = float(row[3].replace("%", "").strip() or 0)
            if rate_val > 0:
                exceptions.append({"step": row[0], "sample_size": row[1], "exceptions": row[2], "rate": row[3]})

        recommendations, _ = _find_recommendations(chunks, most_recent_wp["doc_id"])

    return {
        "benchmark_policy": {
            "policy_id": policy_id,
            "doc_id": benchmark["doc_id"],
            "version": benchmark["version"],
            "effective_date": benchmark.get("effective_date"),
            "control_id": benchmark.get("control_id"),
            "process_area": benchmark.get("process_area"),
        },
        "prior_work_papers_found": [
            {
                "doc_id": wp["doc_id"],
                "audit_cycle": wp.get("audit_cycle"),
                "date_prepared": wp.get("date_prepared"),
                "tested_version": wp.get("tests_policy_version"),
            }
            for wp in work_papers
        ],
        "legacy_checklist": legacy_steps,
        "carried_forward_high_risk_kris": high_kris,
        "prior_exceptions": exceptions,
        "prior_period_recommendations": recommendations,
        "version_gap": bool(most_recent_wp) and most_recent_wp.get("tests_policy_version") != benchmark.get("version"),
    }


def generate_llm_audit_plan(policy_id: str, metadata_index: list[dict], chunks: list[dict]) -> dict[str, Any]:
    context = _gather_context(policy_id, metadata_index, chunks)

    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(context, indent=2, ensure_ascii=False)),
    ]
    response = llm.invoke(messages)

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    parsed = json.loads(raw)

    return {
        "benchmark_policy": context["benchmark_policy"],
        "prior_work_papers_found": context["prior_work_papers_found"],
        "version_gap": context["version_gap"],
        "audit_steps": parsed["audit_steps"],
    }
