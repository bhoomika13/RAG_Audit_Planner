"""BH7 - retrieval and grounding.

This stage queries the Chroma vector index built in BH6 and retrieves the most
relevant evidence for a natural-language audit question.

The retrieval is intentionally structured in two parts:
1) current-policy evidence only (filter is_current=True)
2) related prior-work evidence (filter doc_type='work_paper')

Usage:
    python run_bh7.py "What credit rating requires escalation before booking an order?"
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

ROOT = Path(__file__).resolve().parent
VECTOR_DIR = ROOT / "data" / "vector_index"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name="audit_corpus",
        embedding_function=HuggingFaceEmbeddings(model_name=MODEL),
        persist_directory=str(VECTOR_DIR),
    )


def show_results(label: str, results) -> None:
    print(f"\n--- {label} ---")
    if not results:
        print("  No results found.")
        return

    for idx, (doc, score) in enumerate(results, start=1):
        meta = doc.metadata
        snippet = doc.page_content.replace("\n", " ")[:180]
        print(f"[{idx}] score={score:.3f} | doc_id={meta.get('doc_id')} | page={meta.get('page_number')} | type={meta.get('chunk_type')} | current={meta.get('is_current')}")
        print(f"    policy_id={meta.get('policy_id')} | version={meta.get('version')} | doc_type={meta.get('doc_type')}")
        print(f"    {snippet}...")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_bh7.py \"<your natural language question>\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"QUESTION: {question}\n")

    vector_store = get_vector_store()

    policy_results = vector_store.similarity_search_with_score(
        question,
        k=3,
        filter={"is_current": True},
    )
    prior_work_results = vector_store.similarity_search_with_score(
        question,
        k=3,
        filter={"doc_type": "work_paper"},
    )

    show_results("Current policy evidence (is_current=True)", policy_results)
    show_results("Prior work evidence (doc_type='work_paper')", prior_work_results)

    print("\nBH7 summary:")
    print("- policy evidence is filtered to active/current policy versions")
    print("- prior work evidence shows related historical audit work")
    print("- these retrieved chunks are the grounding set for the next planner step")


if __name__ == "__main__":
    main()
