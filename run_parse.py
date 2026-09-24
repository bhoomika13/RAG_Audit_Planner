"""
BH2 runner — parses every PDF in output_pdfs/ (the BH1 source inventory)
and writes one structured JSON file per document to data/parsed/.

Usage: python run_parse.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from parsing.extract import OCR_ENGINE_AVAILABLE, parse_pdf  # noqa: E402

SOURCE_DIR = os.path.join(os.path.dirname(__file__), "output_pdfs")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "parsed")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"OCR engine available: {OCR_ENGINE_AVAILABLE}\n")

    pdf_files = sorted(f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".pdf"))
    if not pdf_files:
        print(f"No PDFs found in {SOURCE_DIR}")
        return

    for fname in pdf_files:
        src_path = os.path.join(SOURCE_DIR, fname)
        result = parse_pdf(src_path)

        out_path = os.path.join(OUT_DIR, os.path.splitext(fname)[0] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        n_tables = sum(1 for p in result["pages"] for b in p["blocks"] if b["block_type"] == "table")
        methods = {p["extraction_method"] for p in result["pages"]}
        print(f"{fname}: {result['num_pages']} pages, {n_tables} table blocks, "
              f"extraction={sorted(methods)} -> {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
