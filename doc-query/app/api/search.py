from fastapi import APIRouter
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
from app.services.llm_service import generate_answer

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

def process_citations(answer: str, context_blocks: list[dict]):
    """
    Extracts citations from the LLM answer, renumbers them sequentially,
    and returns only the dynamically cited context blocks.
    Only processes citations outside fenced code blocks to avoid corrupting
    array indexing syntax like arr[0], items[1], etc.
    """
    code_block_pattern = re.compile(r'(```[^\n]*\n[\s\S]*?```)', re.MULTILINE)
    segments = code_block_pattern.split(answer)
    
    # Collect cited indices only from non-code segments
    cited_indices = set()
    for segment in segments:
        if not code_block_pattern.match(segment):
            for match in re.finditer(r'\[(\d+)\]', segment):
                cited_indices.add(int(match.group(1)))
        
    sorted_cited_indices = sorted(list(cited_indices))
    
    index_mapping = {}
    filtered_blocks = []
    
    new_idx = 1
    for old_idx in sorted_cited_indices:
        block = next((b for b in context_blocks if b["source_index"] == old_idx), None)
        if block:
            index_mapping[old_idx] = new_idx
            new_block = dict(block)
            new_block["source_index"] = new_idx
            filtered_blocks.append(new_block)
            new_idx += 1
            
    def replace_cit(match):
        old_val = int(match.group(1))
        if old_val in index_mapping:
            return f"[{index_mapping[old_val]}]"
        # If the LLM hallucinated a citation that doesn't exist, strip the brackets
        # so it doesn't render as a broken interactive link on the UI
        return f"{old_val}" 
    
    #apply citation replacement only to non-code segments
    new_segments = []
    for segment in segments:
        if code_block_pattern.match(segment):
            new_segments.append(segment)
        else:
            new_segments.append(re.sub(r'\[(\d+)\]', replace_cit, segment))
    
    new_answer = "".join(new_segments)
    return new_answer, filtered_blocks

@router.post(
    "/search",
    response_model=SearchResponse
)
def search(request: SearchRequest):
    
    retrieval_output = retrieve(request.query)
    
    confidence_score = float(retrieval_output["retrieval_confidence"]["score"])
    
    answer = generate_answer(
        request.query,
        retrieval_output
    )
    
    # Process citations to strictly map UI dropdown to LLM generated citations
    mapped_answer, mapped_blocks = process_citations(answer, retrieval_output["context_blocks"])
    
    # Reconstruct sources from context blocks
    sources = []
    for block in mapped_blocks:
        url = build_document_url(block["doc_path"])
        # get title from doc_path (e.g. docs/guides/setup.md -> setup.md)
        title = block["doc_path"].split("/")[-1] if block["doc_path"] else "Untitled"
        sources.append({
            "doc_id": "", 
            "doc_path": block["doc_path"],
            "url": url,
            "chunk_text": block["text"],
            "similarity": float(block.get("best_similarity", confidence_score / 100.0)),
            "title": title
        })
    
    return {
        "answer": mapped_answer,
        "confidence_score": confidence_score,
        "sources": sources
    }