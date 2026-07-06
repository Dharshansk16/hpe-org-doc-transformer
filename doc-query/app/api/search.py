from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import os
import re
from dotenv import load_dotenv

# Load frontend/.env to get GitHub config
load_dotenv()

from app.models.search_models import (
    SearchRequest,
    SearchResponse
)

from app.services.retrieval_service import retrieve
from app.services.llm_service import generate_answer_stream

router = APIRouter()

def build_document_url(doc_path: str):
    if not doc_path:
        return ""
        
    github_org = os.getenv("GITHUB_ORG", "")
    github_repo = os.getenv("GITHUB_REPO", "")
    
    if not (github_org and github_repo):
        return ""
        
    # Remove leading slash from doc_path if present to avoid double slashes
    doc_path = doc_path.lstrip("/")
    
    return f"https://github.com/{github_org}/{github_repo}/blob/main/{doc_path}"

@router.post("/search")
def search_stream(request: SearchRequest):
    retrieval_output = retrieve(request.query)
    confidence_score = float(retrieval_output["retrieval_confidence"]["score"])
    
    sources = []
    for block in retrieval_output["context_blocks"]:
        url = build_document_url(block["doc_path"])
        title = block["doc_path"].split("/")[-1] if block["doc_path"] else "Untitled"
        sources.append({
            "doc_id": "", 
            "doc_path": block["doc_path"],
            "url": url,
            "chunk_text": block["text"],
            "similarity": float(block.get("best_similarity", confidence_score / 100.0)),
            "title": title,
            "source_index": block["source_index"]
        })
    
    def event_generator():
        meta_data = {
            "type": "meta",
            "confidence_score": confidence_score,
            "sources": sources
        }
        yield f"data: {json.dumps(meta_data)}\n\n"
        
        for chunk in generate_answer_stream(request.query, retrieval_output):
            chunk_data = {
                "type": "chunk",
                "text": chunk
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            
        yield "data: {\"type\": \"done\"}\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")