"""AB test harness -- ingest, query, score, report."""

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

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # teams/team5/backend/
REPO_ROOT = BACKEND_DIR.parent.parent.parent  # /home/.../Hackathon-BOM-IKNL/
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
    seen_urls: set[str] = set()

    for url, text in pages.items():
        norm_url = url.strip().rstrip("/")
        if norm_url.startswith("https://kanker.nl/"):
            norm_url = norm_url.replace("https://kanker.nl/", "https://www.kanker.nl/", 1)

        if norm_url in seen_urls:
            continue
        seen_urls.add(norm_url)

        meta = sitemap.get(norm_url)
        if meta is None:
            continue

        # Use full hash to avoid collisions
        url_hash = hashlib.md5(norm_url.encode()).hexdigest()

        if is_hybrid:
            result = chunker_fn(text)
            chunks = result.get("fine", [])
            for i, chunk in enumerate(result.get("coarse", [])):
                doc_id = f"{variant_name}_{url_hash}_c{i}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metas.append({**meta, "tier": "coarse", "url": meta["url"]})
            for i, chunk in enumerate(chunks):
                doc_id = f"{variant_name}_{url_hash}_f{i}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metas.append({**meta, "tier": "fine", "url": meta["url"]})
        else:
            chunks = chunker_fn(text)
            for i, chunk in enumerate(chunks):
                doc_id = f"{variant_name}_{url_hash}_{i}"
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
