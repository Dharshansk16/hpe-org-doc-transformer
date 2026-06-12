

import json

from doc_types.state import ClassifierState
from embedding.embedder import generate_embedding
from db import insert_doc_embedding_cache, search_similar_prototypes, search_similar_buffer, search_similar_segments
from config.settings import get_settings
import logging 

settings = get_settings()
logger = logging.getLogger(__name__)

def decide_route(state: ClassifierState) -> ClassifierState:
    content = state.get("fingerprint", "")
    if isinstance(content, dict):
        content = content.get("fingerprint", "") or json.dumps(content)
    if content is None:
        content = ""
    embedding = list(generate_embedding("search_query: " + content))
    state["embedding"] = embedding

    groups = search_similar_groups(embedding)
   
    state["similar_group_candidates"] = groups[:settings.min_groups_for_review] if len(groups) >= settings.min_groups_for_review else groups
    state["top_similarity_score"] = groups[0]["similarity"] if groups else 0.0
    if not groups:
        state["create_new_group"] = True
        state["classification_route"] = "CREATE_NEW_GROUP"
    elif groups[0]["similarity"] >= settings.auto_assign_threshold:
        state["create_new_group"] = False
        state["classification_route"] = "AUTO_ASSIGN"
        state["existing_group_id"] = groups[0]["id"]
    else:
        state["create_new_group"] = False
        state["classification_route"] = "REVIEW_BY_AGENT"

       
        try:
            insert_doc_embedding_cache(state["doc_id"], embedding)
        except Exception as cache_exc:
            logger.warning(
                "decide_route: failed to cache embedding for doc '%s': %s",
                state.get("doc_id"),
                cache_exc,
            )

    return state


def search_similar_groups(embedding: list[float]) -> list[dict]:
    """Search all three sources and merge results.

    Always queries prototypes, buffer, and segments so that a
    high-similarity match in a lower-priority source is never
    silently dropped.
    """

    #Prototype hits
    similar_prototypes = search_similar_prototypes(
        embedding=embedding,
        limit=20,
        min_similarity=settings.review_threshold,
    )
    proto_groups = aggregate_group_candidates(similar_prototypes or [], source="prototype")

    #buffer hits
    similar_buffers = search_similar_buffer(
        embedding=embedding,
        limit=20,
        min_similarity=settings.review_threshold,
    )
    buffer_groups = aggregate_group_candidates(similar_buffers or [], source="buffer")

    #Segment hits (broadest coverage, slightly lower threshold)
    similar_segments = search_similar_segments(
        embedding=embedding,
        limit=20,
        min_similarity=settings.review_threshold - 0.03,
    )
    segment_groups = aggregate_group_candidates(similar_segments or [], source="segment")

    # Merge all three
    merged = merge_group_candidates(proto_groups, buffer_groups)
    merged = merge_group_candidates(merged, segment_groups)

    return merged


def aggregate_group_candidates(rows: list[dict], source: str = "unknown") -> list[dict]:
    """Aggregate raw search rows into per-group candidates with multi-hit scoring.

    Instead of keeping only the single best similarity, we track all
    hits and compute a weighted score that rewards groups with many
    consistent matches:  0.7 * max_similarity + 0.3 * avg_similarity
    """
    grouped: dict[str, dict] = {}
    for row in rows:
        group_id = row.get("id")
        if not group_id:
            continue

        similarity = float(row.get("similarity", 0.0))
        existing = grouped.get(group_id)

        if existing is None:
            grouped[group_id] = {
                "id": group_id,
                "name": row.get("name"),
                "doc_count": row.get("doc_count"),
                "proto_count": row.get("proto_count"),
                "max_similarity": similarity,
                "total_similarity": similarity,
                "hit_count": 1,
                "top_proto_index": row.get("proto_index"),
                "source": source,
            }
        else:
            existing["hit_count"] += 1
            existing["total_similarity"] += similarity
            if similarity > existing["max_similarity"]:
                existing["max_similarity"] = similarity
                existing["top_proto_index"] = row.get("proto_index")

    results: list[dict] = []
    for g in grouped.values():
        avg_sim = g["total_similarity"] / g["hit_count"]
        # Weighted score: strong single match + consistent multi-hit bonus
        score = 0.7 * g["max_similarity"] + 0.3 * avg_sim
        results.append({
            "id": g["id"],
            "name": g["name"],
            "doc_count": g["doc_count"],
            "proto_count": g["proto_count"],
            "similarity": round(score, 6),
            "max_similarity": round(g["max_similarity"], 6),
            "hit_count": g["hit_count"],
            "top_proto_index": g["top_proto_index"],
            "source": g["source"],
        })

    return sorted(results, key=lambda item: item["similarity"], reverse=True)


def merge_group_candidates(primary: list[dict], fallback: list[dict]) -> list[dict]:
    """Merge two candidate lists, keeping the entry with the higher score per group."""
    merged: dict[str, dict] = {g["id"]: g for g in primary}

    for group in fallback:
        group_id = group["id"]
        if group_id not in merged:
            merged[group_id] = group
        else:
            existing = merged[group_id]
            #accumulate hits from both sources for a richer signal
            combined_hits = existing["hit_count"] + group["hit_count"]
            combined_total = (
                existing.get("max_similarity", existing["similarity"]) * existing["hit_count"]
                + group.get("max_similarity", group["similarity"]) * group["hit_count"]
            )
            combined_max = max(
                existing.get("max_similarity", existing["similarity"]),
                group.get("max_similarity", group["similarity"]),
            )
            combined_avg = combined_total / combined_hits
            combined_score = 0.7 * combined_max + 0.3 * combined_avg

            merged[group_id] = {
                **existing,
                "similarity": round(combined_score, 6),
                "max_similarity": round(combined_max, 6),
                "hit_count": combined_hits,
                #keep the top_proto_index from whichever had the higher max
                "top_proto_index": (
                    group["top_proto_index"]
                    if group.get("max_similarity", group["similarity"]) > existing.get("max_similarity", existing["similarity"])
                    else existing["top_proto_index"]
                ),
            }

    return sorted(merged.values(), key=lambda g: g["similarity"], reverse=True)
