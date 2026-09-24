"""
BH5 - Chunking strategy (structure-aware; keep tables intact).

Takes the flat, page-level LangChain Documents produced by BH4
(data/ingested/_documents.jsonl) and splits each page into retrieval-sized
chunks, with one hard rule: a table block is NEVER split across chunks. It is
always emitted as exactly one chunk, however large, because splitting a table
mid-row would make its numbers unrecoverable/ungroundable for the audit
planner (e.g. a risk-score row separated from its "Action Required" column).

Ordinary paragraph/heading text is grouped into runs between tables and fed
through a normal LangChain RecursiveCharacterTextSplitter, so long sections
still get split to a sensible embedding-sized chunk.

Every chunk keeps all BH3/BH4 document-level metadata (doc_id, policy_id,
version, status, is_current, control_id, ...) plus chunk-level fields
(chunk_id, chunk_index, chunk_type, page_number).
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


def _render_table(block: dict[str, Any]) -> str:
    return "\n".join(" | ".join(c or "" for c in row) for row in block.get("rows", []))


def _group_blocks_into_segments(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Consecutive 'line' blocks become one text run; each 'table' block is its own segment."""
    segments: list[dict[str, Any]] = []
    text_run: list[dict[str, Any]] = []

    def flush():
        if text_run:
            segments.append({"type": "text", "blocks": list(text_run)})
            text_run.clear()

    for block in blocks:
        if block["block_type"] == "table":
            flush()
            segments.append({"type": "table", "block": block})
        else:
            text_run.append(block)
    flush()
    return segments


def chunk_page(page_doc: LCDocument, splitter: RecursiveCharacterTextSplitter) -> list[LCDocument]:
    parent_meta = {k: v for k, v in page_doc.metadata.items() if k != "blocks"}
    segments = _group_blocks_into_segments(page_doc.metadata.get("blocks", []))

    chunks: list[LCDocument] = []
    chunk_index = 0

    for seg in segments:
        if seg["type"] == "table":
            block = seg["block"]
            content = _render_table(block)
            if not content.strip():
                continue
            chunks.append(LCDocument(page_content=content, metadata={
                **parent_meta,
                "chunk_type": "table",
                "chunk_index": chunk_index,
                "n_rows": block.get("n_rows"),
                "n_cols": block.get("n_cols"),
                "table_rows": block.get("rows"),
            }))
            chunk_index += 1
        else:
            text = "\n".join(b.get("text", "") for b in seg["blocks"]).strip()
            if not text:
                continue
            for piece in splitter.split_text(text):
                chunks.append(LCDocument(page_content=piece, metadata={
                    **parent_meta,
                    "chunk_type": "text",
                    "chunk_index": chunk_index,
                }))
                chunk_index += 1

    for c in chunks:
        c.metadata["chunk_id"] = f"{c.metadata.get('doc_id')}_p{c.metadata.get('page_number')}_c{c.metadata['chunk_index']}"
        c.metadata["char_count"] = len(c.page_content)

    return chunks


def chunk_documents(
    page_documents: list[LCDocument],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[LCDocument]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[LCDocument] = []
    for page_doc in page_documents:
        chunks.extend(chunk_page(page_doc, splitter))
    return chunks
