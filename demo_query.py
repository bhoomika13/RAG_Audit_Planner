"""Run a semantic search against theBH6 Chroma vector index.

Usage examples:
    python demo_query.py "What credit rating requires escalation before booking an order?"
    python demo_query.py "How is the FX variance calculated for non-Euro orders?"
    python demo_query.py "Which current policy governs order approval backlog management?"
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

ROOT = Path(__file__).resolve().parent
VECTOR_DIR = ROOT / "data" / "vector_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python demo_query.py \"<your english question>\"")
        print("Example: python demo_query.py \"What credit rating requires escalation before booking an order?\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\nQUESTION: {question}\n")

    vector_store = Chroma(
        collection_name="audit_corpus",
        embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL),
        persist_directory=str(VECTOR_DIR),
    )

    results = vector_store.similarity_search_with_score(question, k=5)
    print(f"Top {len(results)} matching chunks:\n")
    for idx, (doc, score) in enumerate(results, start=1):
        meta = doc.metadata
        snippet = doc.page_content.replace("\n", " ")[:140]
        print(f"[{idx}] score={score:.3f}")
        print(f"    doc_id={meta.get('doc_id')}")
        print(f"    page={meta.get('page_number')}  type={meta.get('chunk_type')}")
        print(f"    policy_id={meta.get('policy_id')}  version={meta.get('version')}  is_current={meta.get('is_current')}")
        print(f"    text={snippet}...")
        print()


if __name__ == "__main__":
    main()
