"""
BH6 runner — embeds every BH5 chunk (data/chunks/_chunks.jsonl) with a local
HuggingFace sentence-transformer and stores them in a local Chroma vector
index (data/vector_index/). Then runs a couple of sanity-check similarity
searches (plain + metadata-filtered) to prove the index actually works before
BH7 builds real hybrid retrieval + reranking on top of it.

Usage: python run_embed.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from embeddings.build_index import EMBEDDING_MODEL_NAME, build_vector_store  # noqa: E402
from langchain_core.documents import Document as LCDocument  # noqa: E402

CHUNKS_JSONL = os.path.join(os.path.dirname(__file__), "data", "chunks", "_chunks.jsonl")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "data", "vector_index")


def load_chunks(path: str) -> list[LCDocument]:
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            docs.append(LCDocument(page_content=obj["page_content"], metadata=obj["metadata"]))
    return docs


def show_results(label: str, results) -> None:
    print(f"\n--- {label} ---")
    for doc, score in results:
        snippet = doc.page_content.replace("\n", " ")[:80]
        print(f"  score={score:.3f}  [{doc.metadata.get('doc_id')} p{doc.metadata.get('page_number')} "
              f"{doc.metadata.get('chunk_type')}]  {snippet}...")


def main():
    if not os.path.exists(CHUNKS_JSONL):
        print(f"Missing {CHUNKS_JSONL} - run run_chunk.py (BH5) first.")
        return

    chunks = load_chunks(CHUNKS_JSONL)
    print(f"Embedding {len(chunks)} chunks with '{EMBEDDING_MODEL_NAME}' (local, CPU)...")

    vector_store = build_vector_store(chunks, INDEX_DIR)

    n_indexed = vector_store._collection.count()
    print(f"\nIndexed {n_indexed} vectors -> {os.path.relpath(INDEX_DIR)}")

    # sanity check 1: plain similarity search
    q1 = "What credit rating requires escalation before booking an order?"
    show_results(f"Query: '{q1}'", vector_store.similarity_search_with_score(q1, k=3))

    # sanity check 2: same query, but only against currently in-force policies
    # (this is the "version-in-force filter" BH7 will build on properly)
    show_results(
        f"Same query, filtered to is_current=True",
        vector_store.similarity_search_with_score(q1, k=3, filter={"is_current": True}),
    )

    # sanity check 3: a table-heavy question, to confirm table chunks embed usefully
    q3 = "How is the FX variance calculated for non-Euro orders?"
    show_results(f"Query: '{q3}'", vector_store.similarity_search_with_score(q3, k=3))

    if n_indexed != len(chunks):
        print(f"\nWARNING: indexed count ({n_indexed}) != chunk count ({len(chunks)})")
    else:
        print(f"\nNo warnings — all {len(chunks)} chunks embedded and indexed successfully.")


if __name__ == "__main__":
    main()
