"""Five chunking strategies for AB testing.

Each function takes text and returns a list of chunk strings.
Variant A reuses existing code. Variants B-E implement alternatives.
"""

import re
import numpy as np
from ingestion.vectorize import chunk_text, chunk_markdown
from tests.ab_chunking.preprocess import strip_boilerplate, split_sentences


# ---------------------------------------------------------------------------
# Variant A: Baseline (current implementation)
# ---------------------------------------------------------------------------

def chunk_baseline(text: str, is_markdown: bool = False) -> list[str]:
    """Current fixed-window chunker. No preprocessing."""
    if is_markdown:
        return [chunk for chunk, _title in chunk_markdown(text)]
    return chunk_text(text)


# ---------------------------------------------------------------------------
# Variant B: Sentence-aware
# ---------------------------------------------------------------------------

def chunk_sentence_aware(
    text: str,
    max_words: int = 300,
    overlap_words: int = 50,
    is_markdown: bool = False,
) -> list[str]:
    """Split on sentence boundaries, merge up to max_words."""
    cleaned = strip_boilerplate(text) if not is_markdown else text
    sentences = split_sentences(cleaned)
    if not sentences:
        return [cleaned] if cleaned.strip() else []

    chunks = []
    current_chunk: list[str] = []
    current_words = 0

    for sent in sentences:
        sent_words = len(sent.split())
        if current_words + sent_words > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Overlap: keep last few sentences that fit within overlap_words
            overlap_chunk: list[str] = []
            overlap_count = 0
            for s in reversed(current_chunk):
                sw = len(s.split())
                if overlap_count + sw > overlap_words:
                    break
                overlap_chunk.insert(0, s)
                overlap_count += sw
            current_chunk = overlap_chunk + [sent]
            current_words = overlap_count + sent_words
        else:
            current_chunk.append(sent)
            current_words += sent_words

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# ---------------------------------------------------------------------------
# Variant C: Paragraph-level
# ---------------------------------------------------------------------------

def chunk_paragraph(
    text: str,
    max_words: int = 400,
    min_words: int = 50,
    is_markdown: bool = False,
) -> list[str]:
    """One chunk per paragraph (newline-delimited). Merge short paragraphs."""
    cleaned = strip_boilerplate(text) if not is_markdown else text
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    if not lines:
        return [cleaned] if cleaned.strip() else []

    chunks = []
    buffer = ""

    for line in lines:
        line_words = len(line.split())
        buffer_words = len(buffer.split()) if buffer else 0

        if buffer and buffer_words + line_words > max_words:
            chunks.append(buffer.strip())
            buffer = line
        elif buffer_words < min_words or buffer_words + line_words <= max_words:
            buffer = f"{buffer}\n{line}" if buffer else line
        else:
            chunks.append(buffer.strip())
            buffer = line

    if buffer.strip():
        chunks.append(buffer.strip())

    return chunks


# ---------------------------------------------------------------------------
# Variant D: Semantic chunking
# ---------------------------------------------------------------------------

def chunk_semantic(
    text: str,
    threshold: float = 0.75,
    embedding_fn=None,
    is_markdown: bool = False,
) -> list[str]:
    """Split when cosine similarity between adjacent sentence embeddings drops.

    Requires an embedding function that takes a list of strings and returns
    a list of numpy arrays (or list of lists).
    """
    cleaned = strip_boilerplate(text) if not is_markdown else text
    sentences = split_sentences(cleaned)
    if len(sentences) <= 1:
        return [cleaned.strip()] if cleaned.strip() else []

    if embedding_fn is None:
        from connectors.embeddings import get_embedding_function
        ef = get_embedding_function()
        embeddings = ef(sentences)
    else:
        embeddings = embedding_fn(sentences)

    # Convert to numpy for cosine similarity
    emb_array = np.array(embeddings)

    # Compute cosine similarity between adjacent sentences
    chunks = []
    current_group: list[str] = [sentences[0]]

    for i in range(1, len(sentences)):
        a = emb_array[i - 1]
        b = emb_array[i]
        cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)

        if cos_sim < threshold:
            # Similarity drop — start new chunk
            chunks.append(" ".join(current_group))
            current_group = [sentences[i]]
        else:
            current_group.append(sentences[i])

    if current_group:
        chunks.append(" ".join(current_group))

    return chunks


# ---------------------------------------------------------------------------
# Variant E: Hybrid (coarse + fine)
# ---------------------------------------------------------------------------

def chunk_hybrid(
    text: str,
    fine_max_words: int = 200,
    is_markdown: bool = False,
) -> dict[str, list[str]]:
    """Two-tier chunking: coarse (full text) + fine (paragraph-level).

    Returns a dict with "coarse" and "fine" keys instead of a flat list.
    The harness handles querying both tiers and merging results.
    """
    cleaned = strip_boilerplate(text) if not is_markdown else text

    # Coarse: full page/section as a single chunk
    coarse = [cleaned.strip()] if cleaned.strip() else []

    # Fine: paragraph-level chunks
    fine = chunk_paragraph(cleaned, max_words=fine_max_words, is_markdown=is_markdown)

    return {"coarse": coarse, "fine": fine}


# ---------------------------------------------------------------------------
# Registry: name -> function mapping
# ---------------------------------------------------------------------------

KANKER_NL_CHUNKERS = {
    "A_baseline": lambda text: chunk_baseline(text, is_markdown=False),
    "B_sentence": lambda text: chunk_sentence_aware(text, is_markdown=False),
    "C_paragraph": lambda text: chunk_paragraph(text, is_markdown=False),
    "D_semantic": lambda text: chunk_semantic(text, is_markdown=False),
    "E_hybrid": lambda text: chunk_hybrid(text, is_markdown=False),
}

PUBLICATION_CHUNKERS = {
    "A_baseline": lambda text: chunk_baseline(text, is_markdown=True),
    "B_section": lambda text: chunk_paragraph(text, max_words=2000, is_markdown=True),
    "C_small": lambda text: chunk_sentence_aware(text, max_words=150, overlap_words=30, is_markdown=True),
    "D_semantic": lambda text: chunk_semantic(text, is_markdown=True),
    "E_hybrid": lambda text: chunk_hybrid(text, fine_max_words=200, is_markdown=True),
}
