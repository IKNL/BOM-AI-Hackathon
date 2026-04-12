"""kanker.nl vector search connector.

Provides semantic search over patient-facing cancer information pages
from kanker.nl, stored in a ChromaDB collection. Supports metadata
filtering by kankersoort (cancer type) and section.
"""
from __future__ import annotations

import logging
from typing import Optional

import chromadb

from connectors.base import Citation, SourceConnector, SourceResult
from paths import resolve_repo_path

logger = logging.getLogger(__name__)

COLLECTION_NAME = "kanker_nl"
DEFAULT_N_RESULTS = 5


class KankerNLConnector(SourceConnector):
    """Vector search connector for kanker.nl patient information."""

    name = "kanker_nl"
    description = (
        "Search the kanker.nl patient information database for general information "
        "about cancer types, diagnosis, treatment options, side effects, and life "
        "after diagnosis. Content is in Dutch. Optionally filter by cancer type "
        "(kankersoort) and section."
    )

    def __init__(self, chromadb_path: str = "data/chromadb") -> None:
        from connectors.embeddings import get_embedding_function
        self._chromadb_path = resolve_repo_path(chromadb_path)
        self._embedding_function = get_embedding_function()
        self._client = chromadb.PersistentClient(path=self._chromadb_path)
        self._collection = None
        self._resolve_collection()

    def _resolve_collection(self) -> None:
        """(Re)bind the collection handle. Tolerates the collection being
        missing or rebuilt while the backend is running."""
        try:
            self._collection = self._client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_function,
            )
            logger.info(
                "KankerNLConnector bound to '%s' (%d documents)",
                COLLECTION_NAME,
                self._collection.count(),
            )
        except Exception as exc:
            self._collection = None
            logger.warning(
                "KankerNLConnector could not bind to '%s': %s",
                COLLECTION_NAME,
                exc,
            )

    async def query(self, **params) -> SourceResult:
        """Dispatch to search_kanker_nl with the provided parameters."""
        return await search_kanker_nl(
            self,
            query=params.get("query", ""),
            kankersoort=params.get("kankersoort"),
            section=params.get("section"),
            n_results=params.get("n_results", DEFAULT_N_RESULTS),
        )


async def search_kanker_nl(
    connector: KankerNLConnector,
    query: str,
    kankersoort: Optional[str] = None,
    section: Optional[str] = None,
    n_results: int = DEFAULT_N_RESULTS,
) -> SourceResult:
    """Search kanker.nl content with optional metadata filters.

    Parameters
    ----------
    connector:
        An initialised KankerNLConnector instance.
    query:
        Free-text search query.
    kankersoort:
        Optional cancer type slug to filter on (e.g. "borstkanker").
    section:
        Optional section filter (e.g. "behandelingen", "diagnose").
    n_results:
        Maximum number of chunks to return.

    Returns
    -------
    SourceResult
        Contains matched text passages, a human-readable summary,
        and citations with kanker.nl URLs.
    """
    try:
        # Re-bind lazily if the collection wasn't available at startup
        # (e.g. ingestion hadn't run yet, or is rebuilding right now).
        if connector._collection is None:
            connector._resolve_collection()
        if connector._collection is None:
            return SourceResult(
                data=[],
                summary="De kanker.nl database is op dit moment niet beschikbaar.",
                sources=[],
                visualizable=False,
            )

        # Build query kwargs
        query_kwargs: dict = {
            "query_texts": [query],
            "n_results": n_results,
        }

        # Apply metadata filters
        where_clause = _build_where_clause(kankersoort, section, connector)
        if where_clause is not None:
            query_kwargs["where"] = where_clause

        try:
            results = connector._collection.query(**query_kwargs)
        except Exception as inner_exc:
            # The collection may have been deleted/rebuilt under us. Try once more.
            logger.warning(
                "kanker_nl query failed (%s), re-resolving collection and retrying",
                inner_exc,
            )
            connector._resolve_collection()
            if connector._collection is None:
                return SourceResult(
                    data=[],
                    summary="De kanker.nl database is op dit moment niet beschikbaar.",
                    sources=[],
                    visualizable=False,
                )
            results = connector._collection.query(**query_kwargs)

        # Extract documents and metadata from ChromaDB response
        documents = results["documents"][0] if results["documents"][0] else []
        metadatas = results["metadatas"][0] if results["metadatas"][0] else []

        if not documents:
            return SourceResult(
                data=[],
                summary="Geen resultaten gevonden op kanker.nl voor deze zoekopdracht.",
                sources=[],
                visualizable=False,
            )

        # Deduplicate citations by URL
        seen_urls: set[str] = set()
        citations: list[Citation] = []
        for meta in metadatas:
            url = meta.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                citations.append(
                    Citation(
                        url=url,
                        title=meta.get("title", "kanker.nl"),
                        reliability="official",
                    )
                )

        summary = (
            f"Gevonden: {len(documents)} relevante passage(s) op kanker.nl"
        )
        if kankersoort:
            summary += f" over {kankersoort}"
        if section:
            summary += f" in sectie '{section}'"
        summary += "."

        return SourceResult(
            data=documents,
            summary=summary,
            sources=citations,
            visualizable=False,
        )

    except Exception as exc:
        logger.exception("Error querying kanker.nl collection: %s", exc)
        return SourceResult(
            data=[],
            summary=f"Er is een fout opgetreden bij het doorzoeken van kanker.nl: {exc}",
            sources=[],
            visualizable=False,
        )


# Known kankersoort slugs from the sitemap — used for exact-match filtering.
# Populated lazily from the ChromaDB collection at first use.
_KNOWN_SLUGS: set[str] = set()


def _normalize_kankersoort(raw: str) -> str:
    """Normalize a cancer type string to match sitemap slugs."""
    return raw.lower().strip().replace(" ", "-")


def _resolve_kankersoort_slug(raw: str, connector: "KankerNLConnector") -> str | None:
    """Find the best matching kankersoort slug from the known set.

    Returns the exact slug if found, or checks for prefix/substring matches.
    Returns None if no match (let semantic search handle relevance instead).
    """
    global _KNOWN_SLUGS
    if not _KNOWN_SLUGS and connector._collection is not None:
        try:
            # Get unique kankersoort values from the collection
            sample = connector._collection.get(limit=1, include=["metadatas"])
            if sample and sample["metadatas"]:
                # Fetch a larger sample to build the slug set
                all_meta = connector._collection.get(
                    limit=connector._collection.count(),
                    include=["metadatas"],
                )
                _KNOWN_SLUGS = {
                    m.get("kankersoort", "")
                    for m in all_meta["metadatas"]
                    if m.get("kankersoort")
                }
        except Exception:
            pass

    slug = _normalize_kankersoort(raw)

    # Exact match
    if slug in _KNOWN_SLUGS:
        return slug

    # Prefix/substring match (e.g. "darmkanker" matches "darmkanker-dikkedarmkanker")
    matches = [s for s in _KNOWN_SLUGS if slug in s or s in slug]
    if len(matches) == 1:
        return matches[0]

    # Multiple or no matches — skip filter, let semantic search handle it
    return None


def _build_where_clause(
    kankersoort: Optional[str],
    section: Optional[str],
    connector: Optional["KankerNLConnector"] = None,
) -> dict | None:
    """Build a ChromaDB where clause from optional filters.

    Returns None if no filters are provided or if no exact slug match is found
    (in which case semantic search handles relevance via the query text).
    """
    filters: list[dict] = []

    if kankersoort and connector is not None:
        slug = _resolve_kankersoort_slug(kankersoort, connector)
        if slug:
            filters.append({"kankersoort": {"$eq": slug}})
    if section:
        filters.append({"section": {"$eq": section}})

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}
