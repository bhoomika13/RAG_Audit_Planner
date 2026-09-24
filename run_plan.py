"""
BH8 runner — builds the audit plan from BH3 metadata (data/metadata/_index.json)
and BH5 chunks (data/chunks/_chunks.jsonl), writes data/audit_plan/audit_plan.json,
and prints a summary table plus per-item detail (objective, priority, carried
forward KRIs/findings/recommendations, evidence chunk_ids).

Usage: python run_plan.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from planning.generate_plan import build_audit_plan  # noqa: E402

METADATA_INDEX = os.path.join(os.path.dirname(__file__), "data", "metadata", "_index.json")
CHUNKS_JSONL = os.path.join(os.path.dirname(__file__), "data", "chunks", "_chunks.jsonl")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "audit_plan")


def load_jsonl(path: str) -> list[dict]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def main() -> None:
    if not os.path.exists(METADATA_INDEX):
        print(f"Missing {METADATA_INDEX} - run run_metadata.py (BH3) first.")
        return
    if not os.path.exists(CHUNKS_JSONL):
        print(f"Missing {CHUNKS_JSONL} - run run_chunk.py (BH5) first.")
        return

    with open(METADATA_INDEX, encoding="utf-8") as f:
        metadata_index = json.load(f)
    chunks = load_jsonl(CHUNKS_JSONL)

    items = build_audit_plan(metadata_index, chunks)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "audit_plan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([it.to_dict() for it in items], f, indent=2, ensure_ascii=False)

    print(f"{'policy_id':<14} {'active':<8} {'prior_tested':<14} {'gap':<7} {'priority':<9} {'high_kris':<10} {'exceptions'}")
    for it in items:
        print(f"{it.policy_id:<14} {it.active_version:<8} {str(it.prior_tested_version):<14} "
              f"{str(it.version_gap):<7} {it.priority:<9} {len(it.open_high_risk_kris):<10} {len(it.exception_findings)}")
    print(f"\nWrote {len(items)} planned audit items -> {os.path.relpath(out_path)}")

    print("\n" + "=" * 90)
    print("DETAILED PLANNED AUDIT ITEMS")
    print("=" * 90)
    for it in items:
        print(f"\n[{it.priority}] {it.policy_id} -> {it.active_doc_id}")
        print(f"  Objective: {it.objective}")
        if it.prior_work_doc_id:
            print(f"  Prior work: {it.prior_work_doc_id} (tested v{it.prior_tested_version}, cycle {it.prior_audit_cycle})")
        if it.open_high_risk_kris:
            print("  Carried-forward HIGH risk KRIs:")
            for k in it.open_high_risk_kris:
                print(f"    - {k['kri_id']}: {k['description']} ({k['clause']})")
        if it.exception_findings:
            print("  Prior exceptions noted:")
            for e in it.exception_findings:
                print(f"    - step {e['step']}: {e['exceptions']}/{e['sample_size']} ({e['rate']})")
        if it.carried_forward_recommendations:
            print("  Carried-forward recommendations:")
            for r in it.carried_forward_recommendations:
                print(f"    - {r}")
        print(f"  Evidence chunk_ids: {', '.join(it.evidence_chunk_ids) if it.evidence_chunk_ids else 'none'}")


if __name__ == "__main__":
    main()
