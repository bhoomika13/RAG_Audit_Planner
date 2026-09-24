"""
BH4 - Ingest documents into the retrieval pipeline (LangChain-native).

Merges BH2 parsed content with BH3 metadata into one canonical
`langchain_core.documents.Document` per PAGE (page_content + metadata),
validates the merge, and exposes a Corpus that hands BH5 (chunking) a flat
list of LangChain Documents ready to split/embed.

Each page-level Document's metadata carries both page-level fields
(page_number, extraction_method, blocks) AND the document-level fields BH3
produced (doc_id, policy_id, version, status, is_current, control_id,
supersedes/superseded_by, tests_policy_doc_id, ...) so BH7's "version-in-force
filter" can filter directly on the flattened Documents without a join.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

from langchain_core.documents import Document as LCDocument

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from parsing.extract import parsed_to_documents  # noqa: E402

# metadata fields propagated from the BH3 record onto every page Document
DOC_LEVEL_FIELDS = [
    "doc_id", "doc_type", "policy_id", "version", "status", "is_current",
    "control_id", "process_area", "owner", "effective_date", "superseded_date",
    "supersedes", "superseded_by", "audit_cycle", "date_prepared",
    "tests_policy_id", "tests_policy_version", "tests_policy_doc_id",
]


@dataclass
class IngestedFile:
    doc_id: str
    doc_type: str
    metadata: dict[str, Any]
    pages: list[LCDocument] = field(default_factory=list)

    @property
    def num_pages(self) -> int:
        return len(self.pages)

    @property
    def num_blocks(self) -> int:
        return sum(len(p.metadata.get("blocks", [])) for p in self.pages)

    @property
    def num_tables(self) -> int:
        return sum(1 for p in self.pages for b in p.metadata.get("blocks", []) if b["block_type"] == "table")


class Corpus:
    """In-memory registry of ingested files, with the lookups BH5-BH7 need."""

    def __init__(self, files: list[IngestedFile]):
        self._by_id = {f.doc_id: f for f in files}

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self):
        return iter(self._by_id.values())

    def get(self, doc_id: str) -> IngestedFile | None:
        return self._by_id.get(doc_id)

    def policies(self) -> list[IngestedFile]:
        return [f for f in self if f.doc_type == "policy"]

    def work_papers(self) -> list[IngestedFile]:
        return [f for f in self if f.doc_type == "work_paper"]

    def active_policy(self, policy_id: str) -> IngestedFile | None:
        for f in self.policies():
            if f.metadata.get("policy_id") == policy_id and f.metadata.get("is_current"):
                return f
        return None

    def work_papers_for_policy(self, policy_doc_id: str) -> list[IngestedFile]:
        return [f for f in self.work_papers() if f.metadata.get("tests_policy_doc_id") == policy_doc_id]

    def iter_documents(self) -> list[LCDocument]:
        """Flat list of every page-level LangChain Document across the whole corpus — the hand-off point for BH5."""
        return [page for f in self for page in f.pages]


def _load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_corpus(parsed_dir: str, metadata_dir: str) -> tuple[Corpus, list[str]]:
    """Merges BH2 parsed content with BH3 metadata into LangChain Documents. Returns (corpus, warnings)."""
    warnings: list[str] = []

    metadata_files = sorted(f for f in os.listdir(metadata_dir) if f.endswith(".json") and f != "_index.json")
    parsed_files = {f for f in os.listdir(parsed_dir) if f.endswith(".json")}

    files: list[IngestedFile] = []
    seen_doc_ids: set[str] = set()
    referenced_parsed_files: set[str] = set()

    for fname in metadata_files:
        meta = _load_json(os.path.join(metadata_dir, fname))
        doc_id = meta.get("doc_id")

        if not doc_id:
            warnings.append(f"{fname}: metadata has no doc_id, skipping")
            continue
        if doc_id in seen_doc_ids:
            warnings.append(f"{doc_id}: duplicate doc_id across metadata files")
            continue
        seen_doc_ids.add(doc_id)

        parsed_rel_path = meta.get("parsed_json_path")
        parsed_fname = os.path.basename(parsed_rel_path) if parsed_rel_path else None
        if not parsed_fname or parsed_fname not in parsed_files:
            warnings.append(f"{doc_id}: parsed_json_path '{parsed_rel_path}' not found, skipping")
            continue
        referenced_parsed_files.add(parsed_fname)

        parsed_doc = _load_json(os.path.join(parsed_dir, parsed_fname))
        pages = parsed_to_documents(parsed_doc)
        if not pages or not any(p.page_content.strip() for p in pages):
            warnings.append(f"{doc_id}: parsed document has no content blocks")

        doc_level = {k: meta.get(k) for k in DOC_LEVEL_FIELDS}
        for page in pages:
            page.metadata.update(doc_level)

        files.append(IngestedFile(doc_id=doc_id, doc_type=meta.get("doc_type", "unknown"),
                                   metadata=meta, pages=pages))

    orphan_parsed = parsed_files - referenced_parsed_files
    for fname in sorted(orphan_parsed):
        warnings.append(f"{fname}: parsed file has no matching metadata record (orphan)")

    active_counts: dict[str, int] = {}
    for f in files:
        if f.doc_type == "policy":
            pid = f.metadata.get("policy_id")
            if f.metadata.get("is_current"):
                active_counts[pid] = active_counts.get(pid, 0) + 1
    for pid, count in active_counts.items():
        if count != 1:
            warnings.append(f"{pid}: expected exactly 1 active/current version at ingestion, found {count}")

    return Corpus(files), warnings


def persist_corpus(corpus: Corpus, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for f in corpus:
        out = {
            "doc_id": f.doc_id,
            "doc_type": f.doc_type,
            "metadata": f.metadata,
            "num_pages": f.num_pages,
            "num_blocks": f.num_blocks,
            "num_tables": f.num_tables,
            "pages": [{"page_content": p.page_content, "metadata": p.metadata} for p in f.pages],
        }
        with open(os.path.join(out_dir, f.doc_id + ".json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)

    index = [
        {
            "doc_id": f.doc_id,
            "doc_type": f.doc_type,
            "policy_id": f.metadata.get("policy_id"),
            "version": f.metadata.get("version"),
            "status": f.metadata.get("status"),
            "is_current": f.metadata.get("is_current"),
            "num_pages": f.num_pages,
            "num_blocks": f.num_blocks,
            "num_tables": f.num_tables,
        }
        for f in corpus
    ]
    with open(os.path.join(out_dir, "_corpus_index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)


def persist_documents_jsonl(corpus: Corpus, path: str) -> None:
    """Flat list of every page Document (page_content + metadata), one JSON object per line — the direct BH5 input."""
    with open(path, "w", encoding="utf-8") as f:
        for doc in corpus.iter_documents():
            f.write(json.dumps({"page_content": doc.page_content, "metadata": doc.metadata}, ensure_ascii=False) + "\n")
