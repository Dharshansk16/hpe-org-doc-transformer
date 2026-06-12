from __future__ import annotations
import logging
from typing import Any
from classifier.ingestion.prototypes import assign_group, compute_medoids
from db import write_to_db
from db.prototypes import refresh_doc_count, fetch_all_group_embeddings, upsert_prototypes, clear_buffer, update_proto_count


logger = logging.getLogger(__name__)

DOC_PREFIX = "search_document: "


def ingest_document(
    doc_id: str,
    doc_path: str | None,
    group_id: str | None,
    content: str,
    doc_info: dict[str, Any] | None = None,
    chunks: list[dict[str, Any]] | None = None,
    segments: list[dict[str, Any]] | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    

    segment_count = len(segments) if segments else 0
    total_chunks = len(chunks) if chunks else 0

    old_group_id = None
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT group_id FROM documents WHERE id = %s", [doc_id])
            row = cursor.fetchone()
            if row:
                old_group_id = row.get("group_id")

    write_to_db(
            conn,
            doc_id,
            doc_path,
            group_id,
            content,
            segment_count,
            total_chunks,
            chunks or [],
            segments or [],
        )
    assign_group(doc_id, group_id, segments or [], conn=conn)

    if old_group_id and old_group_id != group_id and conn:
        refresh_doc_count(old_group_id, conn)
        old_embeddings = fetch_all_group_embeddings(old_group_id, conn)
        if old_embeddings:
            new_protos = compute_medoids(old_embeddings)
            upsert_prototypes(old_group_id, new_protos, conn)
            clear_buffer(old_group_id, conn)
            update_proto_count(old_group_id, len(new_protos), conn)
        else:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM group_prototypes WHERE group_id = %s", [old_group_id])
            update_proto_count(old_group_id, 0, conn)
    
    logger.info("ingest_document: document ingested successfully (doc_id=%s)", doc_id)
    logger.info("ingest_document: document assigned to group_id=%s", group_id)
    
    return {
        "doc_id": doc_id,
        "doc_path": doc_path,
        "content": content,
        "doc_info": doc_info,
        "chunks": chunks,
        "segments": segments,
        "n_chunks": len(chunks),
        "n_segments": len(segments),
    }

