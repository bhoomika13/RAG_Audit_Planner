"""
BH3 runner — reads every BH2 parsed JSON in data/parsed/, extracts metadata
(policy id, version, effective date, control id, ...), cross-links versions
of the same policy (supersedes / superseded_by / is_current), and writes:
  - data/metadata/<doc>.json   (one metadata record per source document)
  - data/metadata/_index.json  (all records combined, for BH4+ to load in one shot)

Usage: python run_metadata.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from metadata.extract_metadata import extract_metadata, link_versions  # noqa: E402

PARSED_DIR = os.path.join(os.path.dirname(__file__), "data", "parsed")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "metadata")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    json_files = sorted(f for f in os.listdir(PARSED_DIR) if f.lower().endswith(".json"))
    if not json_files:
        print(f"No parsed JSON files found in {PARSED_DIR}")
        return

    all_metadata = []
    for fname in json_files:
        path = os.path.join(PARSED_DIR, fname)
        with open(path, encoding="utf-8") as f:
            parsed_doc = json.load(f)
        meta = extract_metadata(parsed_doc, os.path.relpath(path))
        all_metadata.append(meta)

    warnings = link_versions(all_metadata)

    for meta in all_metadata:
        out_path = os.path.join(OUT_DIR, meta["doc_id"] + ".json") if meta["doc_id"] else \
            os.path.join(OUT_DIR, "UNKNOWN_" + str(len(os.listdir(OUT_DIR))) + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    index_path = os.path.join(OUT_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)

    print(f"{'doc_id':<18} {'type':<11} {'status':<11} {'effective':<10} {'supersedes':<20} {'superseded_by'}")
    for m in sorted(all_metadata, key=lambda d: (d["doc_type"], d["doc_id"] or "")):
        print(f"{m['doc_id']:<18} {m['doc_type']:<11} {str(m['status']):<11} "
              f"{str(m['effective_date']):<10} {str(m.get('supersedes')):<20} {m.get('superseded_by')}")

    print(f"\nWrote {len(all_metadata)} metadata records + index to {os.path.relpath(OUT_DIR)}")

    if warnings:
        print(f"\n{len(warnings)} data-quality warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nNo data-quality warnings.")


if __name__ == "__main__":
    main()
