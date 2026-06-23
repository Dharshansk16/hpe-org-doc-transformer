import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tokenizers import Tokenizer
from typing import Any

_tokenizer = Tokenizer.from_pretrained("nomic-ai/nomic-embed-text-v1")

def _count_tokens(text: str) -> int:
    return len(_tokenizer.encode(text, add_special_tokens=False))


def _make_splitter(chunk_size: int, overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=_count_tokens,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        keep_separator=True,
    )

_CHUNK_RULES: dict[str, tuple[int, int]] = {
    "prose":    (512, 64),
    "report":   (1024, 128),
    "code":     (384, 48),
    "list":     (256, 32),
    "short":    (0, 0), 
}

# Regex to match fenced code blocks (``` or ~~~ with optional language tag).
# Uses a backreference (\2) so the closing fence matches the opening fence style.
_CODE_FENCE_RE = re.compile(
    r'(?:^|\n)([ \t]*(`{3,}|~{3,})[^\n]*\n[\s\S]*?\n[ \t]*\2[ \t]*(?:\n|$))',
    re.MULTILINE,
)

# Sentinel that is safe for PostgreSQL TEXT, tokenizers, and string ops.
# Must not appear in real document content.
_SENTINEL = "__CODEBLOCK_PLACEHOLDER"


def _protect_code_blocks(text: str) -> tuple[str, dict[str, str]]:
    """
    Replace fenced code blocks with unique placeholders so the text splitter
    cannot split them. Returns the modified text and a mapping of
    placeholder -> original code block content.
    """
    placeholders: dict[str, str] = {}
    counter = 0

    def _replace(match: re.Match) -> str:
        nonlocal counter
        code_block = match.group(1)
        # The placeholder is a single token-like string so the splitter
        # will never split inside it.
        placeholder = f"{_SENTINEL}_{counter}__"
        placeholders[placeholder] = code_block
        counter += 1
        # Preserve a leading newline so the surrounding prose stays separated.
        leading = "\n" if match.group(0).startswith("\n") else ""
        return f"{leading}{placeholder}\n"

    protected = _CODE_FENCE_RE.sub(_replace, text)
    return protected, placeholders


def _restore_code_blocks(chunks: list[str], placeholders: dict[str, str]) -> list[str]:
    """
    Replace placeholders back with original code block content in each chunk.
    """
    if not placeholders:
        return chunks

    restored = []
    for chunk in chunks:
        for placeholder, original in placeholders.items():
            if placeholder in chunk:
                chunk = chunk.replace(placeholder, original)
        # Strip any leftover sentinel fragments (defensive)
        if _SENTINEL in chunk and not any(p in chunk for p in placeholders):
            chunk = re.sub(rf"{re.escape(_SENTINEL)}_\d+__", "", chunk)
        restored.append(chunk)
    return restored


def chunk_document(text: str, doc_info: dict) -> list[dict[str, Any]]:
    doc_type = doc_info.get("doc_type") or "prose"
    title    = doc_info.get("title") or ""

    if doc_type == "short":
        chunk_text = f"{title}\n\n{text}" if title else text
        return [{
            "chunk_index": 0,
            "chunk_text":  chunk_text,
            "word_count":  len(chunk_text.split()),
            "token_count": _count_tokens(chunk_text),
        }]

    chunk_size, overlap = _CHUNK_RULES.get(doc_type, _CHUNK_RULES["prose"])
    splitter = _make_splitter(chunk_size, overlap)

    
    source = f"{title}\n\n{text}" if title else text

    # Protect fenced code blocks from being split
    protected_source, placeholders = _protect_code_blocks(source)
    raw_chunks = splitter.split_text(protected_source)
    # Restore code blocks inside each chunk
    raw_chunks = _restore_code_blocks(raw_chunks, placeholders)

    return [
        {
            "chunk_index": i,
            "chunk_text":  chunk,
            "word_count":  len(chunk.split()),
            "token_count": _count_tokens(chunk),
        }
        for i, chunk in enumerate(raw_chunks)
    ]
