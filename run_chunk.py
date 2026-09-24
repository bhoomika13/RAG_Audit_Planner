"""
BH5 runner — loads the flat page-level LangChain Documents BH4 produced
(data/ingested/_documents.jsonl), splits them into structure-aware chunks
(tables kept intact, text split to embedding-sized pieces), and writes:
  - data/chunks/_chunks.jsonl   (flat list, one chunk Document per line -> BH6 input)
  - data/chunks/<doc_id>.json   (chunks grouped by source document, for inspection)
  - data/chunks/_chunks_index.json (per-document chunk stats)

Usage: python run_chunk.py
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from chunking.chunk import chunk_documents  # noqa: E402
from langchain_core.documents import Document as LCDocument  # noqa: E402

INGESTED_DIR = os.path.join(os.path.dirname(__file__), "data", "ingested")
DOCUMENTS_JSONL = os.path.join(INGESTED_DIR, "_documents.jsonl")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "chunks")


def load_page_documents(path: str) -> list[LCDocument]:
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            docs.append(LCDocument(page_content=obj["page_content"], metadata=obj["metadata"]))
    return docs


def main():
    if not os.path.exists(DOCUMENTS_JSONL):
        print(f"Missing {DOCUMENTS_JSONL} - run run_ingest.py (BH4) first.")
        return

    page_documents = load_page_documents(DOCUMENTS_JSONL)
    chunks = chunk_documents(page_documents)

    # sanity check: every table chunk's row count matches what BH2 originally extracted
    warnings = []
    for c in chunks:
        if c.metadata["chunk_type"] == "table":
            expected = c.metadata.get("n_rows")
            actual = len(c.metadata.get("table_rows") or [])
            if expected != actual:
                warnings.append(f"{c.metadata['chunk_id']}: table row count mismatch (expected {expected}, got {actual})")

    os.makedirs(OUT_DIR, exist_ok=True)

    by_doc = defaultdict(list)
    for c in chunks:
        by_doc[c.metadata.get("doc_id")].append(c)

    for doc_id, doc_chunks in by_doc.items():
        with open(os.path.join(OUT_DIR, f"{doc_id}.json"), "w", encoding="utf-8") as f:
            json.dump([{"page_content": c.page_content, "metadata": c.metadata} for c in doc_chunks],
                      f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUT_DIR, "_chunks.jsonl"), "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({"page_content": c.page_content, "metadata": c.metadata}, ensure_ascii=False) + "\n")

    index = []
    print(f"{'doc_id':<18} {'chunks':<7} {'text':<6} {'table':<6} {'avg_chars':<10} {'max_chars'}")
    for doc_id, doc_chunks in sorted(by_doc.items()):
        sizes = [c.metadata["char_count"] for c in doc_chunks]
        n_text = sum(1 for c in doc_chunks if c.metadata["chunk_type"] == "text")
        n_table = sum(1 for c in doc_chunks if c.metadata["chunk_type"] == "table")
        avg_size = round(sum(sizes) / len(sizes)) if sizes else 0
        print(f"{doc_id:<18} {len(doc_chunks):<7} {n_text:<6} {n_table:<6} {avg_size:<10} {max(sizes, default=0)}")
        index.append({"doc_id": doc_id, "num_chunks": len(doc_chunks), "num_text_chunks": n_text,
                       "num_table_chunks": n_table, "avg_char_count": avg_size, "max_char_count": max(sizes, default=0)})

    with open(os.path.join(OUT_DIR, "_chunks_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\n{len(chunks)} total chunks from {len(page_documents)} pages -> {os.path.relpath(OUT_DIR)}")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nNo warnings — every table chunk's row count matches the original extraction.")


if __name__ == "__main__":
    main()
