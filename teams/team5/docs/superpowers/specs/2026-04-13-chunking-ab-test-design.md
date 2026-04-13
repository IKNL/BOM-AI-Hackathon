# Chunking Strategy AB Test — Design Spec

## Goal

Compare 5 chunking strategies for the RAG pipeline and measure which produces the best retrieval quality. Test kanker.nl pages and publications separately, then evaluate hybrid approaches.

## Current State Analysis

### Data Sources

**kanker.nl pages (2,816 pages)**
- Plain text scraped from HTML (no markdown, no headings)
- Average 521 words/page, median 418, range 15–8,939
- Single `\n` line breaks between paragraphs (no `\n\n`)
- ~200 chars boilerplate footer on every page ("Praat mee", "Stel een vraag", etc.)
- Usage pattern: FAQ/lookup ("wat zijn de symptomen van darmkanker?")

**Publications (8 PDFs)**
- Docling-extracted markdown with headings (`#`, `##`, `###`) and tables
- Range: 3 Dutch reports + 5 English scientific papers
- Usage pattern: large reports / complex reasoning

### Current Chunking (Baseline)

**kanker.nl**: `chunk_text()` — naive 375-word fixed window with 38-word overlap. Splits on whitespace (`.split()`), no sentence/paragraph awareness. Boilerplate footer included in chunks. ~43% of pages fit in a single chunk.

**Publications**: `chunk_markdown()` — heading-aware splitter. Splits on `# ` / `## ` / `### `, merges short sections, sub-splits long sections at 375-word boundaries. Slightly better than naive but still word-count-based.

**Embedding model**: `intfloat/multilingual-e5-small` (384 dimensions, cosine similarity)

**ChromaDB**: 2 collections (`kanker_nl`, `publications`), cosine distance, HNSW index

---

## Variants

### Kanker.nl Strategies

| ID | Name | Description |
|----|------|-------------|
| **A** | Fixed window (baseline) | Current: 375-word fixed window, 38-word overlap. No preprocessing. |
| **B** | Sentence-aware | Split on sentence boundaries (`. ` followed by capital letter, or `\n`). Merge sentences up to 300 words. Strip boilerplate footer. 50-word overlap at sentence boundaries. |
| **C** | Paragraph-level | One chunk per `\n`-delimited line. Merge consecutive short lines (<50 words) up to 400 words. Strip boilerplate footer. No overlap (paragraphs are self-contained). |
| **D** | Semantic chunking | Embed each sentence individually. Split when cosine similarity between adjacent sentence embeddings drops below threshold (0.75). Group similar consecutive sentences into chunks. Strip boilerplate footer. |
| **E** | Hybrid (coarse + fine) | Two-tier: (1) full-page text as coarse chunk, (2) paragraph-level chunks as fine chunks. Query both, merge results with coarse providing context boost. Strip boilerplate footer. |

### Publication Strategies

| ID | Name | Description |
|----|------|-------------|
| **A** | Heading-aware (baseline) | Current: `chunk_markdown()` splits on headings, merges short sections, 375-word sub-split. |
| **B** | Section-level | One chunk per heading section (no sub-splitting). Preserves full reasoning chains. Heading prepended. |
| **C** | Small precise | 150-word chunks, 30-word overlap. Heading prepended to each chunk for context. |
| **D** | Semantic chunking | Same approach as kanker.nl variant D but applied to markdown text (strip heading markers first). |
| **E** | Hybrid (coarse + fine) | Two-tier: (1) section-level chunks for coarse retrieval, (2) 200-word sub-chunks for fine retrieval. Query both, merge. |

---

## Metrics

### Primary (retrieval quality)

| Metric | Description | How measured |
|--------|-------------|-------------|
| **Recall@5** | Of the known-relevant pages for a query, how many appear in top 5 results? | Per-query, averaged |
| **Precision@5** | Of the top 5 results, how many are actually relevant? | LLM-judged relevance (0/1) per chunk |
| **MRR** | Mean Reciprocal Rank — how high is the first relevant result? | 1/rank of first relevant result, averaged |

### Secondary (efficiency)

| Metric | Description |
|--------|-------------|
| **Chunk count** | Total chunks per variant (affects index size and query cost) |
| **Avg chunk size** | Mean words per chunk (affects context window usage) |
| **Empty result rate** | % of queries returning 0 relevant chunks |

---

## Test Queries

### Kanker.nl test queries (30 queries)

Three categories, 10 each:

**Symptom queries (direct lookup)**
1. Wat zijn de symptomen van darmkanker?
2. Hoe herken je borstkanker?
3. Welke klachten horen bij longkanker?
4. Symptomen van blaaskanker
5. Wat zijn tekenen van prostaatkanker?
6. Hoe merk je leverkanker?
7. Klachten bij slokdarmkanker
8. Symptomen van eierstokkanker
9. Hoe herken je melanoom?
10. Welke symptomen heeft maagkanker?

**Treatment queries (moderate complexity)**
11. Welke behandelingen zijn er voor borstkanker?
12. Hoe wordt darmkanker behandeld?
13. Wat is immunotherapie bij longkanker?
14. Bestraling bij prostaatkanker
15. Chemotherapie bij eierstokkanker
16. Operatie bij maagkanker
17. Behandeling van melanoom
18. Hormoontherapie bij borstkanker
19. Doelgerichte therapie bij nierkanker
20. Stamceltransplantatie bij leukemie

**Living-with queries (broader context needed)**
21. Hoe ga je om met vermoeidheid na kanker?
22. Wat kan ik verwachten na een darmoperatie?
23. Terugkeer van kanker, wat nu?
24. Seksualiteit na kankerbehandeling
25. Voeding tijdens chemotherapie
26. Werken met kanker
27. Psychische klachten bij kanker
28. Fertiliteit na kankerbehandeling
29. Palliatieve zorg bij kanker
30. Huidklachten door bestraling

### Publication test queries (15 queries)

**Statistical queries**
1. Hoeveel mensen krijgen darmkanker per jaar?
2. Overlevingscijfers borstkanker in Nederland
3. Trends in longkankerbehandeling
4. Verschil in kanker tussen mannen en vrouwen

**Clinical queries**
5. Impact of comorbidities on cancer survival
6. Treatment patterns for small cell lung cancer
7. Ovarian cancer recurrence prediction
8. Head and neck cancer survival rates in Europe

**Complex/cross-document queries**
9. Hoe beïnvloeden comorbiditeiten de overleving bij kanker?
10. Wat zijn de trends in uitgezaaide kanker?
11. Vergelijking behandelingen longkanker stadium I-III
12. Regionale verschillen in kankerincidentie
13. Machine learning voor kankerprognose
14. Veranderingen in darmkankerbehandeling over tijd
15. Overlevingsverschillen hoofd-halskanker internationaal

---

## Relevance Judgments

For each query, we pre-define which pages/documents are relevant (ground truth). This is done by:

1. For kanker.nl: map each query to known-relevant URLs from the sitemap (based on kankersoort + section matching)
2. For publications: map each query to known-relevant document titles
3. Additionally: use LLM-as-judge to score each retrieved chunk's relevance to the query on a 0-1 scale

---

## Harness Architecture

```
ab_test_chunking.py
├── chunkers/
│   ├── baseline.py          # Variant A: current chunk_text / chunk_markdown
│   ├── sentence_aware.py    # Variant B
│   ├── paragraph_level.py   # Variant C
│   ├── semantic.py          # Variant D
│   └── hybrid.py            # Variant E
├── evaluate.py              # Run queries, collect metrics
├── judge.py                 # LLM-as-judge relevance scoring
├── queries.json             # Test queries + ground truth
└── results/                 # Output JSON per run
```

**Flow:**
1. For each variant, re-chunk the source data into a temporary ChromaDB collection
2. Run all test queries against the collection
3. Score results using ground truth + LLM judge
4. Collect metrics
5. Output structured JSON with per-query and aggregate results

**Isolation:** Each variant gets its own ChromaDB collection name (e.g., `kanker_nl_A`, `kanker_nl_B`). Collections are deleted and recreated for each test run to ensure clean state.

---

## Boilerplate Stripping

All variants except A (baseline) strip the kanker.nl footer boilerplate. Detection: remove everything after the last occurrence of any of these markers:
- "Meer over"
- "GroepenPraat mee"
- "Heb je gevonden wat je zocht"
- "LotgenotenVind lotgenoten"

This is a preprocessing step applied before chunking.

---

## Decision Criteria

- **Ship**: Variant wins on Recall@5 AND MRR by >5% over baseline, with no regression >5% on any other metric
- **Drill down**: Winner identified but has tunable parameters (e.g., semantic threshold, chunk size). Loop back with winner as new baseline.
- **Inconclusive**: All variants within 5% of baseline on primary metrics. Ship simplest option.

---

## Scope & Constraints

- Test runs must complete in <30 minutes total (all variants, all queries)
- No external API calls for chunking (embedding model runs locally)
- LLM judge calls use the configured LLM provider (openrouter/gpt-4o-mini)
- Harness code lives in `teams/team5/backend/tests/ab_chunking/`
