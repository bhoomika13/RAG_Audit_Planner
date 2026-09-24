"""One-shot backend demo for the full BH1->BH6 pipeline.

Runs in terminal only and prints stage-by-stage progress for:
- BH1: Sample PDF generation
- BH2: PDF parsing
- BH3: Metadata extraction
- BH4: Corpus ingestion
- BH5: Chunking
- BH6: Embedding + vector index creation

Usage:
    python demo_backend_pipeline.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_stage(name: str, script: str) -> None:
    print(f"\n{'=' * 90}")
    print(f"{name}")
    print(f"{'=' * 90}")
    start = time.time()
    result = subprocess.run(
        [sys.executable, script],
        cwd=str(ROOT),
        shell=False,
    )
    elapsed = time.time() - start
    print(f"\n[{name}] exit_code={result.returncode} elapsed={elapsed:.1f}s")
    if result.returncode != 0:
        raise SystemExit(f"{name} failed with exit code {result.returncode}")


def print_summary() -> None:
    print(f"\n{'=' * 90}")
    print("FINAL BACKEND SUMMARY")
    print(f"{'=' * 90}")

    check = f"""
import json
from pathlib import Path
root = Path(r'{ROOT}')
parsed = sum(1 for p in (root/'data'/'parsed').glob('*.json'))
chunks = sum(1 for _ in open(root/'data'/'chunks'/'_chunks.jsonl', encoding='utf-8'))
print('parsed_json_files=', parsed)
print('chunk_records=', chunks)
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
v = Chroma(
    collection_name='audit_corpus',
    embedding_function=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2'),
    persist_directory=str(root/'data'/'vector_index'),
)
print('vector_index_count=', v._collection.count())
print('vector_db_exists=', (root/'data'/'vector_index'/'chroma.sqlite3').exists())
"""
    subprocess.run([sys.executable, "-c", check], cwd=str(ROOT), check=False)


def main() -> None:
    print("Starting full BH1-BH6 backend demo...")
    print(f"Workspace root: {ROOT}")

    stages = [
        ("BH1 - Generate sample PDFs", "generate_pdfs.py"),
        ("BH2 - Parse PDFs into structured JSON", "run_parse.py"),
        ("BH3 - Extract document metadata", "run_metadata.py"),
        ("BH4 - Ingest parsed + metadata into corpus", "run_ingest.py"),
        ("BH5 - Chunk the corpus for retrieval", "run_chunk.py"),
        ("BH6 - Embed chunks and build vector DB", "run_embed.py"),
    ]

    for name, script in stages:
        run_stage(name, script)

    print_summary()
    print("\nPipeline demo complete: BH1 through BH6 are fully executed in one terminal run.")


if __name__ == "__main__":
    main()
