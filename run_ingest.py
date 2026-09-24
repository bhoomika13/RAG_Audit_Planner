"""
BH4 runner — merges BH2 parsed content (data/parsed/) with BH3 metadata
(data/metadata/) into one canonical Document per source file, validates the
merge, and writes the result to data/ingested/ for BH5+ to consume.

Usage: python run_ingest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from ingestion.ingest import build_corpus, persist_corpus, persist_documents_jsonl  # noqa: E402

PARSED_DIR = os.path.join(os.path.dirname(__file__), "data", "parsed")
METADATA_DIR = os.path.join(os.path.dirname(__file__), "data", "metadata")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "ingested")
DOCUMENTS_JSONL = os.path.join(OUT_DIR, "_documents.jsonl")


def main():
    corpus, warnings = build_corpus(PARSED_DIR, METADATA_DIR)

    print(f"{'doc_id':<18} {'type':<11} {'current':<8} {'pages':<6} {'blocks':<7} {'tables'}")
    for d in sorted(corpus, key=lambda d: (d.doc_type, d.doc_id)):
        print(f"{d.doc_id:<18} {d.doc_type:<11} {str(d.metadata.get('is_current')):<8} "
              f"{d.num_pages:<6} {d.num_blocks:<7} {d.num_tables}")

    persist_corpus(corpus, OUT_DIR)
    persist_documents_jsonl(corpus, DOCUMENTS_JSONL)
    n_docs = len(corpus.iter_documents())
    print(f"\nIngested {len(corpus)} files ({n_docs} LangChain Documents) -> {os.path.relpath(OUT_DIR)}")
    print(f"Flat LangChain Document list for BH5 -> {os.path.relpath(DOCUMENTS_JSONL)}")

    if warnings:
        print(f"\n{len(warnings)} validation warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nNo validation warnings — parsed content and metadata are fully reconciled.")


if __name__ == "__main__":
    main()
