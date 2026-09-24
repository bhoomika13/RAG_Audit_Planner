"""
BH6 - Embeddings + vector index (local now, Azure AI Search later).

Embeds every BH5 chunk with a local HuggingFace sentence-transformer model and
stores the vectors in a local Chroma index with full metadata attached (so
BH7 can filter on is_current / doc_type / policy_id alongside the similarity
search — the "version-in-force filter").

Swapping to Azure AI Search later only means swapping `get_embeddings_model()`
for `AzureOpenAIEmbeddings` and `build_vector_store()` for the `AzureSearch`
vector store — the rest of the pipeline (chunks in, retriever out) is
unaffected because both speak the same LangChain `VectorStore`/`Embeddings`
interfaces.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "audit_corpus"


def get_embeddings_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma only accepts scalar (str/int/float/bool) metadata values and
    rejects None. BH5 chunk metadata carries richer data (e.g. `table_rows` is
    a list of row lists, several link fields can be None) which is fine for
    the JSONL source but must be flattened/dropped for Chroma ingestion. The
    original JSONL is left untouched so downstream stages can still read the
    full structure.
    """
    clean: dict = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (list, dict)):
            clean[key] = json.dumps(value, ensure_ascii=False)
        else:
            clean[key] = value
    return clean


def build_vector_store(chunks: list[LCDocument], persist_directory: str) -> Chroma:
    """Full, deterministic rebuild: clears any existing index before re-embedding."""
    if Path(persist_directory).exists():
        shutil.rmtree(persist_directory)

    sanitized_chunks = [
        LCDocument(page_content=c.page_content, metadata=_sanitize_metadata(c.metadata))
        for c in chunks
    ]
    ids = [c.metadata["chunk_id"] for c in sanitized_chunks]
    return Chroma.from_documents(
        documents=sanitized_chunks,
        embedding=get_embeddings_model(),
        ids=ids,
        collection_name=COLLECTION_NAME,
        persist_directory=persist_directory,
    )
