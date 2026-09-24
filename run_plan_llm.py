"""
BH8 (LLM) runner — generates a GPT-4.1 powered audit plan for one benchmark
policy, grounded in BH3 metadata + BH5 chunks (KRIs, findings, recommendations,
legacy audit-step checklist). Requires Azure OpenAI credentials in a local
.env file (see .env.example) — never hard-code the API key.

Usage:
    python run_plan_llm.py POL-ORD-001
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from planning.llm_plan import generate_llm_audit_plan  # noqa: E402

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


def print_plan(plan: dict) -> None:
    bp = plan["benchmark_policy"]
    print("\nBenchmark policy")
    print(f"  {bp['policy_id']} v{bp['version']}  (doc_id={bp['doc_id']}, control={bp['control_id']}, area={bp['process_area']})")

    print("\nPrior work papers found")
    for wp in plan["prior_work_papers_found"]:
        print(f"  - {wp['doc_id']}  cycle={wp['audit_cycle']}  tested_v{wp['tested_version']}  prepared={wp['date_prepared']}")

    steps = plan["audit_steps"]
    counts = {"new": 0, "updated": 0, "kept": 0, "dropped": 0}
    for s in steps:
        counts[s["status"]] = counts.get(s["status"], 0) + 1

    print(f"\nAudit steps — {counts['new']} new · {counts['updated']} updated · {counts['kept']} kept · {counts['dropped']} dropped")
    for i, s in enumerate(steps, start=1):
        print(f"  {i}. [{s['status']}] {s['description']}")
        print(f"     reason: {s['reason']}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_plan_llm.py <POLICY_ID>  (e.g. POL-ORD-001)")
        sys.exit(1)

    policy_id = sys.argv[1]

    if not os.path.exists(METADATA_INDEX) or not os.path.exists(CHUNKS_JSONL):
        print("Missing BH3 metadata or BH5 chunks - run earlier stages first.")
        return

    with open(METADATA_INDEX, encoding="utf-8") as f:
        metadata_index = json.load(f)
    chunks = load_jsonl(CHUNKS_JSONL)

    try:
        plan = generate_llm_audit_plan(policy_id, metadata_index, chunks)
    except RuntimeError as e:
        print(f"Configuration error: {e}")
        return

    print_plan(plan)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"llm_plan_{policy_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"\nWrote LLM-generated plan -> {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
