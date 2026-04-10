"""
FastAPI application for the Cancer Information Chat system.

Endpoints:
- POST /api/chat/stream  -- SSE streaming chat
- POST /api/feedback     -- store user feedback
- GET  /api/feedback/export -- export feedback as CSV
- GET  /api/health       -- health check
"""

import csv
import io
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from models import ChatRequest, FeedbackEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSE event stub (used when orchestrator is not yet available)
# ---------------------------------------------------------------------------


@dataclass
class _SSEEventStub:
    """Fallback SSEEvent dataclass when orchestrator module is not available."""

    event: str  # "token" | "source_card" | "chart_data" | "done" | "error"
    data: str  # JSON string


# Try importing from orchestrator; fall back to stubs
try:
    from orchestrator import ChatOrchestrator, SSEEvent
except ImportError:
    logger.info(
        "backend.orchestrator not available yet -- using placeholder streaming"
    )
    SSEEvent = _SSEEventStub  # type: ignore[misc]
    ChatOrchestrator = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FEEDBACK_DB_PATH = os.environ.get("FEEDBACK_DB_PATH", "data/feedback.db")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
CHROMADB_PATH = os.environ.get("CHROMADB_PATH", "data/chromadb")

# LiteLLM reads OPENROUTER_API_KEY from env automatically for openrouter models
# Set the model prefix for LiteLLM: openrouter/openai/gpt-4o-mini
if LLM_PROVIDER == "openrouter" and not LLM_MODEL.startswith("openrouter/"):
    LLM_MODEL = f"openrouter/{LLM_MODEL}"
VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Connector + orchestrator initialization
# ---------------------------------------------------------------------------

# Global connectors list -- populated at startup
_connectors: list = []


def _create_orchestrator():
    """Create a new ChatOrchestrator with the current connectors.

    Returns None if the orchestrator module is not yet available.
    """
    if ChatOrchestrator is None:
        return None
    return ChatOrchestrator(connectors=_connectors, model=LLM_MODEL)


def _init_connectors() -> list:
    """Initialize all source connectors.

    Returns a list of connector instances.
    Called once at startup.
    """
    connectors = []

    try:
        from connectors.kanker_nl import KankerNLConnector

        connectors.append(KankerNLConnector(chromadb_path=CHROMADB_PATH))
        logger.info("Loaded kanker_nl connector")
    except Exception as exc:
        logger.warning("Could not load kanker_nl connector: %s", exc)

    try:
        from connectors.nkr_cijfers import NKRCijfersConnector

        connectors.append(NKRCijfersConnector())
        logger.info("Loaded nkr_cijfers connector")
    except Exception as exc:
        logger.warning("Could not load nkr_cijfers connector: %s", exc)

    try:
        from connectors.cancer_atlas import CancerAtlasConnector

        connectors.append(CancerAtlasConnector())
        logger.info("Loaded cancer_atlas connector")
    except Exception as exc:
        logger.warning("Could not load cancer_atlas connector: %s", exc)

    try:
        from connectors.publications import PublicationsConnector

        connectors.append(PublicationsConnector(chromadb_path=CHROMADB_PATH))
        logger.info("Loaded publications connector")
    except Exception as exc:
        logger.warning("Could not load publications connector: %s", exc)

    return connectors


def _check_chromadb_collections() -> list[str]:
    """Check which ChromaDB collections exist. Returns list of collection names."""
    collections: list[str] = []
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMADB_PATH)
        for col in client.list_collections():
            collections.append(col.name if hasattr(col, "name") else str(col))
    except Exception as exc:
        logger.warning("Could not check ChromaDB collections: %s", exc)
    return collections


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connectors and check ChromaDB on startup."""
    global _connectors
    logger.info("Starting up Cancer Information Chat backend...")

    # Initialize connectors (graceful -- missing connectors are logged, not fatal)
    _connectors = _init_connectors()
    connector_names = [
        getattr(c, "name", type(c).__name__) for c in _connectors
    ]
    logger.info("Loaded %d connectors: %s", len(_connectors), connector_names)

    # Check ChromaDB collections
    collections = _check_chromadb_collections()
    logger.info("ChromaDB collections found: %s", collections)

    yield

    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Cancer Information Chat API",
    description=(
        "IKNL Hackathon -- Chat interface over trusted cancer information sources"
    ),
    version=VERSION,
    lifespan=lifespan,
)

# CORS -- allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# SQLite feedback helpers
# ---------------------------------------------------------------------------


async def _ensure_feedback_table(db_path: str) -> None:
    """Create the feedback table if it does not exist."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                rating TEXT NOT NULL,
                comment TEXT,
                query TEXT NOT NULL,
                sources_tried TEXT NOT NULL,
                profile TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )
        await db.commit()


async def _store_feedback(db_path: str, entry: FeedbackEntry) -> str:
    """Store a feedback entry and return its ID."""
    await _ensure_feedback_table(db_path)

    feedback_id = str(uuid.uuid4())
    timestamp = (entry.timestamp or datetime.now(timezone.utc)).isoformat()

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO feedback
                (id, session_id, message_id, rating, comment,
                 query, sources_tried, profile, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                entry.session_id,
                entry.message_id,
                entry.rating,
                entry.comment,
                entry.query,
                json.dumps(entry.sources_tried),
                entry.profile,
                timestamp,
            ),
        )
        await db.commit()

    return feedback_id


async def _export_feedback_csv(db_path: str) -> str:
    """Export all feedback as CSV string."""
    await _ensure_feedback_table(db_path)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM feedback ORDER BY timestamp DESC"
        ) as cursor:
            rows = await cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "message_id",
            "rating",
            "comment",
            "query",
            "sources_tried",
            "profile",
            "timestamp",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["session_id"],
                row["message_id"],
                row["rating"],
                row["comment"],
                row["query"],
                row["sources_tried"],
                row["profile"],
                row["timestamp"],
            ]
        )

    return output.getvalue()


# ---------------------------------------------------------------------------
# Placeholder streaming (used when orchestrator is not yet available)
# ---------------------------------------------------------------------------


async def _placeholder_stream(request: ChatRequest):
    """Yield placeholder SSE events for testing when orchestrator is missing."""
    yield SSEEvent(
        event="token",
        data=json.dumps(
            {
                "text": (
                    f"[Placeholder] Received question about '{request.message}' "
                    f"for profile '{request.profile}'. "
                    "The orchestrator module is not yet available."
                )
            }
        ),
    )
    yield SSEEvent(
        event="done",
        data=json.dumps(
            {
                "message_id": str(uuid.uuid4()),
                "sources_tried": [],
            }
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    collections = _check_chromadb_collections()
    status = "healthy" if len(_connectors) > 0 else "degraded"

    return {
        "status": status,
        "llm_provider": LLM_PROVIDER,
        "chromadb_collections": collections,
        "connectors_loaded": [
            getattr(c, "name", type(c).__name__) for c in _connectors
        ],
        "version": VERSION,
    }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming chat endpoint.

    Accepts a ChatRequest and returns a stream of Server-Sent Events.
    """
    orchestrator = _create_orchestrator()

    async def event_generator():
        if orchestrator is not None:
            async for sse_event in orchestrator.stream(request):
                yield {
                    "event": sse_event.event,
                    "data": sse_event.data,
                }
        else:
            # Fallback: use placeholder stream
            async for sse_event in _placeholder_stream(request):
                yield {
                    "event": sse_event.event,
                    "data": sse_event.data,
                }

    return EventSourceResponse(event_generator())


@app.post("/api/feedback", status_code=201)
async def submit_feedback(entry: FeedbackEntry):
    """Store user feedback on a chat response."""
    feedback_id = await _store_feedback(FEEDBACK_DB_PATH, entry)
    return {"id": feedback_id}


@app.get("/api/feedback/export")
async def export_feedback():
    """Export all feedback entries as CSV."""
    csv_content = await _export_feedback_csv(FEEDBACK_DB_PATH)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="feedback-export.csv"',
        },
    )
