# Chunking AB Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a test harness that compares 5 chunking strategies for both kanker.nl pages and publications, measuring retrieval quality (Recall@5, Precision@5, MRR) with LLM-judged relevance.

**Architecture:** Each chunking strategy is a function with a common interface (`text → list[str]`). A harness ingests all data into isolated ChromaDB collections (one per variant), runs 45 test queries, scores results via LLM-as-judge, and outputs a JSON report with per-query and aggregate metrics.

**Tech Stack:** Python 3.11, ChromaDB, sentence-transformers (`intfloat/multilingual-e5-small`), litellm (for LLM judge), numpy (for cosine similarity in semantic chunking)

---

## File Structure

```
teams/team5/backend/tests/ab_chunking/
├── __init__.py
├── preprocess.py           # Boilerplate stripping, text cleaning
├── chunkers.py             # All 5 chunking strategies (A-E) for both data sources
├── queries.json            # 45 test queries + ground truth relevance
├── harness.py              # Ingest, query, collect results
├── judge.py                # LLM-as-judge relevance scoring
├── metrics.py              # Compute Recall@5, Precision@5, MRR, secondary metrics
├── run.py                  # CLI entry point: python -m tests.ab_chunking.run
├── report.py               # Format results into markdown table
└── results/                # Output directory (gitignored)
```

---

### Task 1: Preprocessing — Boilerplate Stripping

**Files:**
- Create: `tests/ab_chunking/__init__.py`
- Create: `tests/ab_chunking/preprocess.py`
- Test: inline doctests + manual verification

- [ ] **Step 1: Create package and preprocessing module**

Create the directory and the boilerplate stripper. This function is used by all non-baseline variants.

```python
# tests/ab_chunking/__init__.py
"""AB test harness for chunking strategy comparison."""

# tests/ab_chunking/preprocess.py
"""Text preprocessing for chunking AB test."""

import re

BOILERPLATE_MARKERS = [
    "Meer over",
    "GroepenPraat mee",
    "Heb je gevonden wat je zocht",
    "LotgenotenVind lotgenoten",
]


def strip_boilerplate(text: str) -> str:
    """Remove kanker.nl footer boilerplate.

    Finds the earliest occurrence of any boilerplate marker
    and truncates the text there.
    """
    earliest = len(text)
    for marker in BOILERPLATE_MARKERS:
        idx = text.find(marker)
        if idx != -1 and idx < earliest:
            earliest = idx
    result = text[:earliest].strip()
    return result if result else text.strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using period + capital letter and newline boundaries.

    Handles Dutch text where abbreviations are less common than English.
    """
    # Split on newlines first, then on sentence boundaries within each line
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split on ". " followed by uppercase, "? ", "! "
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences
```

- [ ] **Step 2: Verify with sample data**

```bash
cd teams/team5/backend
python3 -c "
from tests.ab_chunking.preprocess import strip_boilerplate, split_sentences
import json

with open('../../../data/kanker_nl_pages_all.json') as f:
    pages = json.load(f)

url = 'https://www.kanker.nl/kankersoorten/darmkanker-dikkedarmkanker/algemeen/symptomen-van-darmkanker'
text = pages[url]['text']
print(f'Original: {len(text)} chars, {len(text.split())} words')
cleaned = strip_boilerplate(text)
print(f'Cleaned:  {len(cleaned)} chars, {len(cleaned.split())} words')
print(f'Removed:  {len(text) - len(cleaned)} chars')
print()
sents = split_sentences(cleaned)
print(f'Sentences: {len(sents)}')
for s in sents[:5]:
    print(f'  - {s[:80]}...' if len(s) > 80 else f'  - {s}')
"
```

Expected: cleaned text is shorter (boilerplate removed), sentences split correctly.

- [ ] **Step 3: Commit**

```bash
git add tests/ab_chunking/__init__.py tests/ab_chunking/preprocess.py
git commit -m "feat(ab-test): add preprocessing — boilerplate stripping and sentence splitting"
```

---

### Task 2: Chunking Strategies

**Files:**
- Create: `tests/ab_chunking/chunkers.py`

All 5 strategies for both data sources in one file. Each function has the signature `(text: str, **kwargs) -> list[str]`. The file imports `chunk_text` and `chunk_markdown` from the existing `ingestion.vectorize` module for variant A.

- [ ] **Step 1: Implement all chunkers**

```python
# tests/ab_chunking/chunkers.py
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
```

- [ ] **Step 2: Verify chunkers with sample data**

```bash
cd teams/team5/backend
python3 -c "
import json
from tests.ab_chunking.chunkers import KANKER_NL_CHUNKERS

with open('../../../data/kanker_nl_pages_all.json') as f:
    pages = json.load(f)

url = 'https://www.kanker.nl/kankersoorten/darmkanker-dikkedarmkanker/algemeen/symptomen-van-darmkanker'
text = pages[url]['text']

for name, fn in KANKER_NL_CHUNKERS.items():
    if name == 'E_hybrid':
        result = fn(text)
        print(f'{name}: coarse={len(result[\"coarse\"])}, fine={len(result[\"fine\"])} chunks')
    else:
        chunks = fn(text)
        avg_words = sum(len(c.split()) for c in chunks) / max(len(chunks), 1)
        print(f'{name}: {len(chunks)} chunks, avg {avg_words:.0f} words')
"
```

Expected: each variant produces different chunk counts. Semantic (D) should be slower due to embedding.

- [ ] **Step 3: Commit**

```bash
git add tests/ab_chunking/chunkers.py
git commit -m "feat(ab-test): implement 5 chunking strategies (baseline, sentence, paragraph, semantic, hybrid)"
```

---

### Task 3: Test Queries and Ground Truth

**Files:**
- Create: `tests/ab_chunking/queries.json`

- [ ] **Step 1: Create test queries with ground truth**

Build `queries.json` with 45 queries. Each query has a `kankersoort` for URL-based ground truth matching and a `category` for analysis grouping.

Ground truth for kanker.nl: a result is relevant if its URL contains the query's `kankersoort` slug AND a relevant section keyword. Ground truth for publications: map queries to document titles.

```json
{
  "kanker_nl": [
    {
      "id": "kn_01",
      "query": "Wat zijn de symptomen van darmkanker?",
      "category": "symptom",
      "kankersoort": "darmkanker",
      "relevant_url_patterns": ["darmkanker", "dikkedarmkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_02",
      "query": "Hoe herken je borstkanker?",
      "category": "symptom",
      "kankersoort": "borstkanker",
      "relevant_url_patterns": ["borstkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_03",
      "query": "Welke klachten horen bij longkanker?",
      "category": "symptom",
      "kankersoort": "longkanker",
      "relevant_url_patterns": ["longkanker"],
      "relevant_sections": ["algemeen", "symptomen", "klachten"]
    },
    {
      "id": "kn_04",
      "query": "Symptomen van blaaskanker",
      "category": "symptom",
      "kankersoort": "blaaskanker",
      "relevant_url_patterns": ["blaaskanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_05",
      "query": "Wat zijn tekenen van prostaatkanker?",
      "category": "symptom",
      "kankersoort": "prostaatkanker",
      "relevant_url_patterns": ["prostaatkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_06",
      "query": "Hoe merk je leverkanker?",
      "category": "symptom",
      "kankersoort": "leverkanker",
      "relevant_url_patterns": ["leverkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_07",
      "query": "Klachten bij slokdarmkanker",
      "category": "symptom",
      "kankersoort": "slokdarmkanker",
      "relevant_url_patterns": ["slokdarmkanker"],
      "relevant_sections": ["algemeen", "symptomen", "klachten"]
    },
    {
      "id": "kn_08",
      "query": "Symptomen van eierstokkanker",
      "category": "symptom",
      "kankersoort": "eierstokkanker",
      "relevant_url_patterns": ["eierstokkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_09",
      "query": "Hoe herken je melanoom?",
      "category": "symptom",
      "kankersoort": "melanoom",
      "relevant_url_patterns": ["melanoom"],
      "relevant_sections": ["algemeen", "symptomen", "herkennen"]
    },
    {
      "id": "kn_10",
      "query": "Welke symptomen heeft maagkanker?",
      "category": "symptom",
      "kankersoort": "maagkanker",
      "relevant_url_patterns": ["maagkanker"],
      "relevant_sections": ["algemeen", "symptomen"]
    },
    {
      "id": "kn_11",
      "query": "Welke behandelingen zijn er voor borstkanker?",
      "category": "treatment",
      "kankersoort": "borstkanker",
      "relevant_url_patterns": ["borstkanker"],
      "relevant_sections": ["behandelingen", "behandeling"]
    },
    {
      "id": "kn_12",
      "query": "Hoe wordt darmkanker behandeld?",
      "category": "treatment",
      "kankersoort": "darmkanker",
      "relevant_url_patterns": ["darmkanker", "dikkedarmkanker"],
      "relevant_sections": ["behandelingen", "behandeling"]
    },
    {
      "id": "kn_13",
      "query": "Wat is immunotherapie bij longkanker?",
      "category": "treatment",
      "kankersoort": "longkanker",
      "relevant_url_patterns": ["longkanker"],
      "relevant_sections": ["behandelingen", "immunotherapie"]
    },
    {
      "id": "kn_14",
      "query": "Bestraling bij prostaatkanker",
      "category": "treatment",
      "kankersoort": "prostaatkanker",
      "relevant_url_patterns": ["prostaatkanker"],
      "relevant_sections": ["behandelingen", "bestraling"]
    },
    {
      "id": "kn_15",
      "query": "Chemotherapie bij eierstokkanker",
      "category": "treatment",
      "kankersoort": "eierstokkanker",
      "relevant_url_patterns": ["eierstokkanker"],
      "relevant_sections": ["behandelingen", "chemotherapie"]
    },
    {
      "id": "kn_16",
      "query": "Operatie bij maagkanker",
      "category": "treatment",
      "kankersoort": "maagkanker",
      "relevant_url_patterns": ["maagkanker"],
      "relevant_sections": ["behandelingen", "operatie"]
    },
    {
      "id": "kn_17",
      "query": "Behandeling van melanoom",
      "category": "treatment",
      "kankersoort": "melanoom",
      "relevant_url_patterns": ["melanoom"],
      "relevant_sections": ["behandelingen", "behandeling"]
    },
    {
      "id": "kn_18",
      "query": "Hormoontherapie bij borstkanker",
      "category": "treatment",
      "kankersoort": "borstkanker",
      "relevant_url_patterns": ["borstkanker"],
      "relevant_sections": ["behandelingen", "hormoontherapie"]
    },
    {
      "id": "kn_19",
      "query": "Doelgerichte therapie bij nierkanker",
      "category": "treatment",
      "kankersoort": "nierkanker",
      "relevant_url_patterns": ["nierkanker"],
      "relevant_sections": ["behandelingen", "doelgerichte"]
    },
    {
      "id": "kn_20",
      "query": "Stamceltransplantatie bij leukemie",
      "category": "treatment",
      "kankersoort": "leukemie",
      "relevant_url_patterns": ["leukemie"],
      "relevant_sections": ["behandelingen", "stamceltransplantatie"]
    },
    {
      "id": "kn_21",
      "query": "Hoe ga je om met vermoeidheid na kanker?",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["vermoeidheid", "gevolgen"],
      "relevant_sections": ["gevolgen", "leven"]
    },
    {
      "id": "kn_22",
      "query": "Wat kan ik verwachten na een darmoperatie?",
      "category": "living_with",
      "kankersoort": "darmkanker",
      "relevant_url_patterns": ["darmkanker", "dikkedarmkanker"],
      "relevant_sections": ["gevolgen", "na-de-behandeling", "operatie"]
    },
    {
      "id": "kn_23",
      "query": "Terugkeer van kanker, wat nu?",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["terugkeer", "recidief"],
      "relevant_sections": ["algemeen", "gevolgen"]
    },
    {
      "id": "kn_24",
      "query": "Seksualiteit na kankerbehandeling",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["seksualiteit", "seksueel"],
      "relevant_sections": ["gevolgen"]
    },
    {
      "id": "kn_25",
      "query": "Voeding tijdens chemotherapie",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["voeding", "eten"],
      "relevant_sections": ["gevolgen", "behandelingen"]
    },
    {
      "id": "kn_26",
      "query": "Werken met kanker",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["werken", "werk"],
      "relevant_sections": ["gevolgen"]
    },
    {
      "id": "kn_27",
      "query": "Psychische klachten bij kanker",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["psychisch", "emotie", "angst"],
      "relevant_sections": ["gevolgen"]
    },
    {
      "id": "kn_28",
      "query": "Fertiliteit na kankerbehandeling",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["fertiliteit", "vruchtbaarheid"],
      "relevant_sections": ["gevolgen"]
    },
    {
      "id": "kn_29",
      "query": "Palliatieve zorg bij kanker",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["palliatieve", "palliatief"],
      "relevant_sections": ["gevolgen", "algemeen"]
    },
    {
      "id": "kn_30",
      "query": "Huidklachten door bestraling",
      "category": "living_with",
      "kankersoort": null,
      "relevant_url_patterns": ["huidklachten", "bestraling", "huid"],
      "relevant_sections": ["gevolgen", "bijwerkingen"]
    }
  ],
  "publications": [
    {
      "id": "pub_01",
      "query": "Hoeveel mensen krijgen darmkanker per jaar?",
      "category": "statistical",
      "relevant_titles": ["Trendrapport darmkanker"]
    },
    {
      "id": "pub_02",
      "query": "Overlevingscijfers borstkanker in Nederland",
      "category": "statistical",
      "relevant_titles": ["Man-vrouwverschillen bij kanker"]
    },
    {
      "id": "pub_03",
      "query": "Trends in longkankerbehandeling",
      "category": "statistical",
      "relevant_titles": ["Trends in treatment of stage I-III NSCLC", "Trends in treatment of stage I-III SCLC"]
    },
    {
      "id": "pub_04",
      "query": "Verschil in kanker tussen mannen en vrouwen",
      "category": "statistical",
      "relevant_titles": ["Man-vrouwverschillen bij kanker"]
    },
    {
      "id": "pub_05",
      "query": "Impact of comorbidities on cancer survival",
      "category": "clinical",
      "relevant_titles": ["Comorbidities and survival in 8 cancers"]
    },
    {
      "id": "pub_06",
      "query": "Treatment patterns for small cell lung cancer",
      "category": "clinical",
      "relevant_titles": ["Trends in treatment of stage I-III SCLC"]
    },
    {
      "id": "pub_07",
      "query": "Ovarian cancer recurrence prediction",
      "category": "clinical",
      "relevant_titles": ["Ovarian cancer recurrence prediction"]
    },
    {
      "id": "pub_08",
      "query": "Head and neck cancer survival rates in Europe",
      "category": "clinical",
      "relevant_titles": ["Head and neck cancers survival in Europe, Taiwan and Japan"]
    },
    {
      "id": "pub_09",
      "query": "Hoe beïnvloeden comorbiditeiten de overleving bij kanker?",
      "category": "complex",
      "relevant_titles": ["Comorbidities and survival in 8 cancers"]
    },
    {
      "id": "pub_10",
      "query": "Wat zijn de trends in uitgezaaide kanker?",
      "category": "complex",
      "relevant_titles": ["Uitgezaaide kanker 2025"]
    },
    {
      "id": "pub_11",
      "query": "Vergelijking behandelingen longkanker stadium I-III",
      "category": "complex",
      "relevant_titles": ["Trends in treatment of stage I-III NSCLC", "Trends in treatment of stage I-III SCLC"]
    },
    {
      "id": "pub_12",
      "query": "Regionale verschillen in kankerincidentie",
      "category": "complex",
      "relevant_titles": ["Man-vrouwverschillen bij kanker", "Uitgezaaide kanker 2025"]
    },
    {
      "id": "pub_13",
      "query": "Machine learning voor kankerprognose",
      "category": "complex",
      "relevant_titles": ["Ovarian cancer recurrence prediction"]
    },
    {
      "id": "pub_14",
      "query": "Veranderingen in darmkankerbehandeling over tijd",
      "category": "complex",
      "relevant_titles": ["Trendrapport darmkanker"]
    },
    {
      "id": "pub_15",
      "query": "Overlevingsverschillen hoofd-halskanker internationaal",
      "category": "complex",
      "relevant_titles": ["Head and neck cancers survival in Europe, Taiwan and Japan"]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add tests/ab_chunking/queries.json
git commit -m "feat(ab-test): add 45 test queries with ground truth relevance mappings"
```

---

### Task 4: LLM Judge

**Files:**
- Create: `tests/ab_chunking/judge.py`

Uses litellm (already a project dependency) to score chunk relevance.

- [ ] **Step 1: Implement LLM-as-judge**

```python
# tests/ab_chunking/judge.py
"""LLM-as-judge for scoring chunk relevance to a query."""

import json
import logging
import os

import litellm

logger = logging.getLogger(__name__)

MODEL = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")


async def judge_relevance(query: str, chunk: str) -> float:
    """Score how relevant a chunk is to a query. Returns 0.0 or 1.0."""
    prompt = f"""You are a relevance judge. Score whether the following text chunk is relevant to the user's query.

Query: "{query}"

Text chunk:
\"\"\"
{chunk[:1500]}
\"\"\"

Is this chunk relevant to answering the query? Reply with ONLY a JSON object:
{{"relevant": true}} or {{"relevant": false}}"""

    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        result = json.loads(clean.strip())
        return 1.0 if result.get("relevant", False) else 0.0
    except Exception as e:
        logger.warning("Judge call failed: %s", e)
        return 0.0


async def judge_batch(query: str, chunks: list[str]) -> list[float]:
    """Score a batch of chunks for relevance to a query."""
    import asyncio
    tasks = [judge_relevance(query, chunk) for chunk in chunks]
    return await asyncio.gather(*tasks)
```

- [ ] **Step 2: Commit**

```bash
git add tests/ab_chunking/judge.py
git commit -m "feat(ab-test): add LLM-as-judge for chunk relevance scoring"
```

---

### Task 5: Metrics Computation

**Files:**
- Create: `tests/ab_chunking/metrics.py`

- [ ] **Step 1: Implement metric functions**

```python
# tests/ab_chunking/metrics.py
"""Compute retrieval quality metrics from query results."""


def recall_at_k(relevant_found: int, total_relevant: int, k: int = 5) -> float:
    """Fraction of known-relevant items found in top-k results."""
    if total_relevant == 0:
        return 0.0
    return min(relevant_found, k) / total_relevant


def precision_at_k(relevance_scores: list[float], k: int = 5) -> float:
    """Fraction of top-k results that are relevant."""
    top_k = relevance_scores[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)


def mrr(relevance_scores: list[float]) -> float:
    """Mean Reciprocal Rank — 1/rank of first relevant result."""
    for i, score in enumerate(relevance_scores):
        if score > 0.5:
            return 1.0 / (i + 1)
    return 0.0


def aggregate_metrics(per_query_results: list[dict]) -> dict:
    """Compute aggregate metrics across all queries.

    Each entry in per_query_results should have:
    - recall_at_5: float
    - precision_at_5: float
    - mrr: float
    """
    n = len(per_query_results)
    if n == 0:
        return {"recall_at_5": 0.0, "precision_at_5": 0.0, "mrr": 0.0}

    return {
        "recall_at_5": sum(r["recall_at_5"] for r in per_query_results) / n,
        "precision_at_5": sum(r["precision_at_5"] for r in per_query_results) / n,
        "mrr": sum(r["mrr"] for r in per_query_results) / n,
    }


def compare_to_baseline(baseline: dict, variant: dict) -> dict:
    """Compute relative improvement over baseline for each metric."""
    result = {}
    for key in baseline:
        b = baseline[key]
        v = variant[key]
        if b > 0:
            result[f"{key}_delta_pct"] = ((v - b) / b) * 100
        else:
            result[f"{key}_delta_pct"] = 0.0 if v == 0 else float("inf")
    return result
```

- [ ] **Step 2: Commit**

```bash
git add tests/ab_chunking/metrics.py
git commit -m "feat(ab-test): add retrieval quality metric functions"
```

---

### Task 6: Test Harness

**Files:**
- Create: `tests/ab_chunking/harness.py`

The core orchestrator: ingest data per variant, run queries, score, collect metrics.

- [ ] **Step 1: Implement the harness**

```python
# tests/ab_chunking/harness.py
"""AB test harness — ingest, query, score, report."""

import hashlib
import json
import logging
import os
from pathlib import Path

import chromadb

from connectors.embeddings import get_embedding_function
from tests.ab_chunking.chunkers import KANKER_NL_CHUNKERS, PUBLICATION_CHUNKERS
from tests.ab_chunking.judge import judge_batch
from tests.ab_chunking.metrics import (
    recall_at_k,
    precision_at_k,
    mrr,
    aggregate_metrics,
    compare_to_baseline,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent.parent
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"
CHROMADB_TEST_PATH = DATA_DIR / "chromadb_ab_test"


def _load_kanker_nl_data() -> dict[str, str]:
    """Load kanker.nl pages. Returns {url: text}."""
    kanker_path = os.environ.get(
        "KANKER_NL_JSON_PATH",
        str(DATA_DIR / "kanker_nl_pages_all.json"),
    )
    with open(kanker_path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    # Filter out broken pages
    return {
        url: page["text"]
        for url, page in pages.items()
        if page.get("text", "").strip()
        and "Error 503" not in page["text"][:200]
        and "pagina die je zocht is helaas niet beschikbaar" not in page["text"][:400]
    }


def _load_sitemap_meta() -> dict[str, dict]:
    """Load sitemap metadata. Returns {url: {kankersoort, section, title}}."""
    sitemap_path = DATA_DIR / "sitemap.json"
    with open(sitemap_path, "r", encoding="utf-8") as f:
        sitemap = json.load(f)
    return {entry["url"]: entry for entry in sitemap}


def _load_queries() -> dict:
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_url_relevant(url: str, query_def: dict) -> bool:
    """Check if a URL matches the ground truth patterns for a query."""
    url_lower = url.lower()
    patterns = query_def.get("relevant_url_patterns", [])
    sections = query_def.get("relevant_sections", [])

    pattern_match = any(p.lower() in url_lower for p in patterns)
    section_match = not sections or any(s.lower() in url_lower for s in sections)

    return pattern_match and section_match


def _is_title_relevant(title: str, query_def: dict) -> bool:
    """Check if a document title matches ground truth for publication queries."""
    relevant_titles = query_def.get("relevant_titles", [])
    return any(rt.lower() in title.lower() or title.lower() in rt.lower() for rt in relevant_titles)


async def run_kanker_nl_test(variant_name: str, chunker_fn, n_results: int = 5) -> dict:
    """Run a single variant test on kanker.nl data. Returns per-query results."""
    ef = get_embedding_function()
    client = chromadb.PersistentClient(path=str(CHROMADB_TEST_PATH))
    collection_name = f"ab_kanker_nl_{variant_name}"

    # Clean slate
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Load data
    pages = _load_kanker_nl_data()
    sitemap = _load_sitemap_meta()

    # Ingest
    all_ids, all_docs, all_metas = [], [], []
    is_hybrid = variant_name == "E_hybrid"

    for url, text in pages.items():
        norm_url = url.strip().rstrip("/")
        if norm_url.startswith("https://kanker.nl/"):
            norm_url = norm_url.replace("https://kanker.nl/", "https://www.kanker.nl/", 1)

        meta = sitemap.get(norm_url)
        if meta is None:
            continue

        if is_hybrid:
            result = chunker_fn(text)
            chunks = result.get("fine", [])
            # Also add coarse chunks with a tier marker
            for i, chunk in enumerate(result.get("coarse", [])):
                doc_id = f"{variant_name}_{hashlib.md5(norm_url.encode()).hexdigest()[:10]}_coarse_{i}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metas.append({**meta, "tier": "coarse", "url": meta["url"]})
            for i, chunk in enumerate(chunks):
                doc_id = f"{variant_name}_{hashlib.md5(norm_url.encode()).hexdigest()[:10]}_fine_{i}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metas.append({**meta, "tier": "fine", "url": meta["url"]})
        else:
            chunks = chunker_fn(text)
            for i, chunk in enumerate(chunks):
                doc_id = f"{variant_name}_{hashlib.md5(norm_url.encode()).hexdigest()[:10]}_{i}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metas.append({"url": meta["url"], "title": meta.get("title", ""), "kankersoort": meta.get("kankersoort", ""), "section": meta.get("section", "")})

    # Batch add
    batch_size = 500
    for i in range(0, len(all_docs), batch_size):
        end = min(i + batch_size, len(all_docs))
        collection.add(ids=all_ids[i:end], documents=all_docs[i:end], metadatas=all_metas[i:end])

    chunk_count = collection.count()
    avg_words = sum(len(d.split()) for d in all_docs) / max(len(all_docs), 1)

    # Run queries
    queries = _load_queries()["kanker_nl"]
    per_query = []

    for q_def in queries:
        results = collection.query(query_texts=[q_def["query"]], n_results=n_results)
        docs = results["documents"][0] if results["documents"][0] else []
        metas = results["metadatas"][0] if results["metadatas"][0] else []

        # Ground truth check: how many returned chunks are from relevant URLs
        url_relevance = [1.0 if _is_url_relevant(m.get("url", ""), q_def) else 0.0 for m in metas]

        # LLM judge
        llm_relevance = await judge_batch(q_def["query"], docs) if docs else []

        # Combined relevance: relevant if EITHER ground truth URL matches OR LLM says relevant
        combined = [max(u, l) for u, l in zip(url_relevance, llm_relevance)] if docs else []

        # Count how many known-relevant URLs exist in the whole collection
        # (simplified: count of unique URLs matching patterns)
        total_relevant = max(sum(url_relevance), 1)

        per_query.append({
            "query_id": q_def["id"],
            "query": q_def["query"],
            "category": q_def["category"],
            "recall_at_5": recall_at_k(sum(1 for r in combined if r > 0.5), total_relevant),
            "precision_at_5": precision_at_k(combined),
            "mrr": mrr(combined),
            "chunks_returned": len(docs),
            "url_matches": sum(url_relevance),
            "llm_matches": sum(llm_relevance),
        })

    # Cleanup
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    return {
        "variant": variant_name,
        "source": "kanker_nl",
        "chunk_count": chunk_count,
        "avg_chunk_words": round(avg_words, 1),
        "per_query": per_query,
        "aggregate": aggregate_metrics(per_query),
    }


async def run_all_kanker_nl() -> list[dict]:
    """Run all kanker.nl variants and return results."""
    results = []
    for name, fn in KANKER_NL_CHUNKERS.items():
        logger.info("Running kanker.nl variant: %s", name)
        result = await run_kanker_nl_test(name, fn)
        results.append(result)
        logger.info("  %s: R@5=%.3f P@5=%.3f MRR=%.3f (%d chunks)",
                     name, result["aggregate"]["recall_at_5"],
                     result["aggregate"]["precision_at_5"],
                     result["aggregate"]["mrr"],
                     result["chunk_count"])
    return results
```

- [ ] **Step 2: Commit**

```bash
git add tests/ab_chunking/harness.py
git commit -m "feat(ab-test): add test harness — ingest, query, score per variant"
```

---

### Task 7: Report Generator

**Files:**
- Create: `tests/ab_chunking/report.py`

- [ ] **Step 1: Implement report formatter**

```python
# tests/ab_chunking/report.py
"""Format AB test results into readable reports."""

import json
from tests.ab_chunking.metrics import compare_to_baseline


def format_report(results: list[dict], source: str) -> str:
    """Format results into a markdown report."""
    lines = [f"# AB Test Results: {source}", ""]

    # Aggregate table
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append("| Variant | Chunks | Avg Words | Recall@5 | Precision@5 | MRR | vs Baseline |")
    lines.append("|---------|--------|-----------|----------|-------------|-----|-------------|")

    baseline_agg = results[0]["aggregate"] if results else {}

    for r in results:
        agg = r["aggregate"]
        delta = compare_to_baseline(baseline_agg, agg) if r != results[0] else {}
        delta_str = " / ".join(
            f"{v:+.1f}%" for k, v in delta.items()
        ) if delta else "—"

        lines.append(
            f"| {r['variant']} | {r['chunk_count']} | {r['avg_chunk_words']} | "
            f"{agg['recall_at_5']:.3f} | {agg['precision_at_5']:.3f} | "
            f"{agg['mrr']:.3f} | {delta_str} |"
        )

    # Per-category breakdown
    lines.append("")
    lines.append("## Per-Category Breakdown")
    categories = sorted(set(q["category"] for r in results for q in r["per_query"]))

    for cat in categories:
        lines.append(f"\n### {cat.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Variant | Recall@5 | Precision@5 | MRR |")
        lines.append("|---------|----------|-------------|-----|")

        for r in results:
            cat_queries = [q for q in r["per_query"] if q["category"] == cat]
            if not cat_queries:
                continue
            n = len(cat_queries)
            avg_r = sum(q["recall_at_5"] for q in cat_queries) / n
            avg_p = sum(q["precision_at_5"] for q in cat_queries) / n
            avg_m = sum(q["mrr"] for q in cat_queries) / n
            lines.append(f"| {r['variant']} | {avg_r:.3f} | {avg_p:.3f} | {avg_m:.3f} |")

    # Decision
    lines.append("")
    lines.append("## Decision")
    lines.append("")

    best = max(results, key=lambda r: r["aggregate"]["recall_at_5"] + r["aggregate"]["mrr"])
    baseline = results[0]
    delta = compare_to_baseline(baseline["aggregate"], best["aggregate"])
    r5_delta = delta.get("recall_at_5_delta_pct", 0)
    mrr_delta = delta.get("mrr_delta_pct", 0)

    if best == baseline:
        lines.append("**Result: Baseline wins.** No alternative improved on both Recall@5 and MRR.")
    elif r5_delta > 5 and mrr_delta > 5:
        lines.append(f"**Result: SHIP `{best['variant']}`** — "
                     f"Recall@5 +{r5_delta:.1f}%, MRR +{mrr_delta:.1f}% over baseline.")
    elif r5_delta > 5 or mrr_delta > 5:
        lines.append(f"**Result: DRILL DOWN on `{best['variant']}`** — "
                     f"Partial improvement (R@5 {r5_delta:+.1f}%, MRR {mrr_delta:+.1f}%). "
                     f"Test sub-variants with tuned parameters.")
    else:
        lines.append("**Result: INCONCLUSIVE** — All variants within 5% of baseline. Ship simplest option.")

    return "\n".join(lines)


def save_results(results: list[dict], source: str, output_dir: str) -> tuple[str, str]:
    """Save raw JSON results and markdown report."""
    from pathlib import Path
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / f"{source}_results.json"
    md_path = out / f"{source}_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    report = format_report(results, source)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)

    return str(json_path), str(md_path)
```

- [ ] **Step 2: Commit**

```bash
git add tests/ab_chunking/report.py
git commit -m "feat(ab-test): add report generator with markdown tables and decision logic"
```

---

### Task 8: CLI Entry Point

**Files:**
- Create: `tests/ab_chunking/run.py`

- [ ] **Step 1: Implement CLI runner**

```python
# tests/ab_chunking/run.py
"""CLI entry point for running the chunking AB test.

Usage:
    cd teams/team5/backend
    python -m tests.ab_chunking.run              # run all
    python -m tests.ab_chunking.run --source kanker_nl  # kanker.nl only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from tests.ab_chunking.harness import run_all_kanker_nl
from tests.ab_chunking.report import save_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = str(Path(__file__).resolve().parent / "results")


async def main(source: str = "all"):
    logger.info("=== Chunking AB Test ===")

    if source in ("all", "kanker_nl"):
        logger.info("Running kanker.nl variants...")
        kn_results = await run_all_kanker_nl()
        json_path, md_path = save_results(kn_results, "kanker_nl", RESULTS_DIR)
        logger.info("Results saved: %s", json_path)
        logger.info("Report saved: %s", md_path)

        # Print report to stdout
        with open(md_path) as f:
            print(f.read())

    logger.info("=== Done ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run chunking AB test")
    parser.add_argument("--source", choices=["all", "kanker_nl", "publications"], default="all")
    args = parser.parse_args()
    asyncio.run(main(args.source))
```

- [ ] **Step 2: Create .gitignore for results directory**

```bash
echo "*" > tests/ab_chunking/results/.gitignore
echo "!.gitignore" >> tests/ab_chunking/results/.gitignore
```

- [ ] **Step 3: Commit**

```bash
git add tests/ab_chunking/run.py tests/ab_chunking/results/.gitignore
git commit -m "feat(ab-test): add CLI entry point for running the AB test"
```

---

### Task 9: Integration Test — Dry Run

- [ ] **Step 1: Run the full harness on kanker.nl data**

```bash
cd teams/team5/backend
python -m tests.ab_chunking.run --source kanker_nl
```

Expected output: a markdown table with 5 rows (A-E) showing Recall@5, Precision@5, MRR for each variant. The report ends with a Ship/Drill down/Inconclusive recommendation.

- [ ] **Step 2: Review results**

Check `tests/ab_chunking/results/kanker_nl_report.md` for the report and `kanker_nl_results.json` for raw data. Verify:
- All 5 variants have results
- All 30 queries were run
- Metrics are in valid ranges (0-1)
- No variant crashed

- [ ] **Step 3: Commit results report**

```bash
git add tests/ab_chunking/results/kanker_nl_report.md
git commit -m "results(ab-test): kanker.nl chunking strategy comparison"
```
