from __future__ import annotations
import logging
from typing import Any
from classifier.ingestion.prototypes import assign_group
from db import  write_to_db
from .chunking import chunk_document
from .detection import detect_doc_info
from .embedding import embed_chunks
from .segments import build_segment_embeddings

logger = logging.getLogger(__name__)

DOC_PREFIX = "search_document: "


def ingest_document(
    doc_id: str,
    doc_path: str | None,
    group_id: str | None,
    content: str,
    doc_info: dict[str, Any] | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    info = doc_info or detect_doc_info(content)

    # [TODO: Dharshan][mid] - move chunking and embeddings and build segments outside transaction 
    chunks = chunk_document(content, info)

    embed_chunks(chunks)
    segments = build_segment_embeddings(chunks)


    write_to_db(doc_id, doc_path, group_id, content, info, chunks, segments, conn)
    
    logger.info("ingest_document: document ingested successfully (doc_id=%s)", doc_id)
    assign_group(doc_id, group_id, segments, conn=conn)
    logger.info("ingest_document: document assigned to group_id=%s", group_id)
    
    return {
        "doc_id": doc_id,
        "doc_path": doc_path,
        "content": content,
        "doc_info": info,
        "chunks": chunks,
        "segments": segments,
        "n_chunks": len(chunks),
        "n_segments": len(segments),
    }

