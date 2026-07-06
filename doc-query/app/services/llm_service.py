import os
from google import genai
from langsmith import traceable

from .prompts import RAG_PROMPT_TEMPLATE

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")



@traceable
def generate_answer_stream(query: str, retrieval_output: dict):
    context_str = "\n\n".join(
        f"[Source {b['source_index']}] {b['doc_path']}\n{b['text']}"
        for b in retrieval_output["context_blocks"]
    )

    sources_str = "\n".join(
        f"[{idx}] {path}"
        for idx, path in retrieval_output["citation_map"].items()
    )

    ret_conf = retrieval_output["retrieval_confidence"]
    retrieval_confidence_str = (
        f"**Retrieval Confidence: {ret_conf['band']} ({ret_conf['score']}%)** "
        f"— {ret_conf['reason']}"
    )

    full_context = f"{retrieval_confidence_str}\n\n{context_str}\n\nSources:\n{sources_str}"

    prompt = RAG_PROMPT_TEMPLATE.format(query=query, context=full_context)
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.strip() == "":
        yield retrieval_confidence_str + "\n\n"
        yield "Sorry, Google API Key is not configured."
        return

    try:
        response = client.models.generate_content_stream(
            model=gemini_model,
            contents=prompt
        )
        yield retrieval_confidence_str + "\n\n"
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Gemini generation failed: {e}")
        yield retrieval_confidence_str + "\n\n"
        yield f"Sorry, Gemini generation failed: {str(e)}"