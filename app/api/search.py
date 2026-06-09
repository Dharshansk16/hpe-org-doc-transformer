from fastapi import APIRouter

from app.models.search_models import (
    SearchRequest,
    SearchResponse
)

from app.services.retrieval_service import (
    retrieve_chunks
)

from app.services.llm_service import generate_answer

router = APIRouter()

@router.post(
    "/search",
    response_model=SearchResponse
)

def search(request: SearchRequest):
    
    chunks = retrieve_chunks(
        query=request.query,
        limit=5
    )
    
    answer = generate_answer(
        request.query,
        chunks
    )
    
    return {
        "answer": answer,
        "sources": [
            {
                "doc_id": chunk["doc_id"],
                "doc_path": chunk["doc_path"]
            }
            for chunk in chunks
        ]
    }