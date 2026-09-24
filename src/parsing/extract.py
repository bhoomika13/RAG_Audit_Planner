"""
BH2 - Document parsing / extraction (table-aware, OCR fallback).

Parses a PDF into a page-by-page, reading-order list of "blocks":
  - table blocks   (extracted as row/column grids, never flattened into prose)
  - text blocks    (regular lines/paragraphs, in top-to-bottom reading order)

If a page yields too little native text (e.g. a scanned/image-only page),
extraction falls back to OCR (PyMuPDF render -> pytesseract). If the Tesseract
OCR engine binary is not installed, the page is still returned with whatever
native text was found and is flagged so downstream steps / a human can see
the gap (see `ocr_engine_available` and `extraction_method`).
"""

from __future__ import annotations

import datetime
import io
from dataclasses import dataclass, field
from typing import Any

import pdfplumber
import pymupdf
import pytesseract
from langchain_core.documents import Document as LCDocument
from PIL import Image

MIN_NATIVE_CHARS = 20  # below this, a page is treated as likely scanned
OCR_RENDER_DPI = 300
TABLE_ROW_TOLERANCE = 3  # px tolerance used to decide if a word sits inside a table bbox


def _check_ocr_engine() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


OCR_ENGINE_AVAILABLE = _check_ocr_engine()


@dataclass
class ParsedBlock:
    block_type: str  # "line" | "table"
    top: float
    text: str | None = None
    rows: list[list[str]] | None = None
    n_rows: int | None = None
    n_cols: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"block_type": self.block_type, "top": round(self.top, 1)}
        if self.block_type == "table":
            d["rows"] = self.rows
            d["n_rows"] = self.n_rows
            d["n_cols"] = self.n_cols
        else:
            d["text"] = self.text
        return d


@dataclass
class ParsedPage:
    page_number: int
    extraction_method: str  # "text" | "ocr" | "text_low_confidence"
    char_count: int
    blocks: list[ParsedBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "extraction_method": self.extraction_method,
            "char_count": self.char_count,
            "blocks": [b.to_dict() for b in self.blocks],
        }


def _bbox_contains_point(bbox: tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, top, x1, bottom = bbox
    return (x0 - TABLE_ROW_TOLERANCE) <= x <= (x1 + TABLE_ROW_TOLERANCE) and \
           (top - TABLE_ROW_TOLERANCE) <= y <= (bottom + TABLE_ROW_TOLERANCE)


def _extract_tables(page: pdfplumber.page.Page) -> list[tuple[tuple[float, float, float, float], list[list[str]]]]:
    found = []
    for table in page.find_tables():
        rows = table.extract()
        # drop fully-empty rows that pdfplumber sometimes emits at table edges
        rows = [r for r in rows if any((c or "").strip() for c in r)]
        if rows:
            found.append((table.bbox, rows))
    return found


def _extract_text_lines(page: pdfplumber.page.Page, table_bboxes: list[tuple[float, float, float, float]]) -> list[tuple[float, str]]:
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    kept = [w for w in words if not any(_bbox_contains_point(bb, (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2) for bb in table_bboxes)]

    # group words into lines by rounded 'top' position
    lines: dict[float, list[dict]] = {}
    for w in kept:
        key = round(w["top"] / 3) * 3  # cluster words within ~3px vertically
        lines.setdefault(key, []).append(w)

    out = []
    for top_key in sorted(lines.keys()):
        line_words = sorted(lines[top_key], key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line_words).strip()
        if text:
            out.append((top_key, text))
    return out


def _ocr_page(pdf_path: str, page_number_zero_based: int) -> str:
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_number_zero_based]
        zoom = OCR_RENDER_DPI / 72
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img)
    finally:
        doc.close()


def parse_pdf(pdf_path: str) -> dict[str, Any]:
    pages_out: list[ParsedPage] = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = _extract_tables(page)
            table_bboxes = [bb for bb, _ in tables]
            text_lines = _extract_text_lines(page, table_bboxes)

            native_text = "".join(t for _, t in text_lines) + "".join(
                c for _, rows in tables for row in rows for c in row if c
            )

            if len(native_text.strip()) >= MIN_NATIVE_CHARS:
                blocks = [ParsedBlock("line", top=top, text=text) for top, text in text_lines]
                blocks += [
                    ParsedBlock("table", top=bb[1], rows=rows, n_rows=len(rows), n_cols=max((len(r) for r in rows), default=0))
                    for bb, rows in tables
                ]
                blocks.sort(key=lambda b: b.top)
                pages_out.append(ParsedPage(i + 1, "text", len(native_text), blocks))
            else:
                # likely scanned / image-only page -> OCR fallback
                if OCR_ENGINE_AVAILABLE:
                    ocr_text = _ocr_page(pdf_path, i)
                    blocks = [ParsedBlock("line", top=float(n), text=ln) for n, ln in enumerate(ocr_text.splitlines()) if ln.strip()]
                    pages_out.append(ParsedPage(i + 1, "ocr", len(ocr_text), blocks))
                else:
                    # can't OCR: keep whatever thin native text/tables we found, flag low confidence
                    blocks = [ParsedBlock("line", top=top, text=text) for top, text in text_lines]
                    blocks += [
                        ParsedBlock("table", top=bb[1], rows=rows, n_rows=len(rows), n_cols=max((len(r) for r in rows), default=0))
                        for bb, rows in tables
                    ]
                    blocks.sort(key=lambda b: b.top)
                    pages_out.append(ParsedPage(i + 1, "text_low_confidence", len(native_text), blocks))

    return {
        "source_file": pdf_path,
        "parsed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "num_pages": len(pages_out),
        "ocr_engine_available": OCR_ENGINE_AVAILABLE,
        "pages": [p.to_dict() for p in pages_out],
    }


def _render_block_text(block: dict[str, Any]) -> str:
    if block["block_type"] == "table":
        return "\n".join(" | ".join(c or "" for c in row) for row in block.get("rows", []))
    return block.get("text", "")


def parsed_to_documents(parsed: dict[str, Any]) -> list[LCDocument]:
    """
    Converts BH2's parsed-page dict (see `parse_pdf`) into LangChain Documents,
    one per page. `page_content` is a flat, readable rendering (tables shown as
    "col | col" rows); the exact structured blocks are kept in `metadata["blocks"]`
    so downstream steps (BH5 chunking) can still treat tables as indivisible units
    instead of relying on the rendered text alone.
    """
    documents = []
    for page in parsed.get("pages", []):
        blocks = page.get("blocks", [])
        page_content = "\n".join(t for t in (_render_block_text(b) for b in blocks) if t)
        documents.append(LCDocument(
            page_content=page_content,
            metadata={
                "source": parsed.get("source_file"),
                "page_number": page["page_number"],
                "extraction_method": page["extraction_method"],
                "blocks": blocks,
            },
        ))
    return documents
