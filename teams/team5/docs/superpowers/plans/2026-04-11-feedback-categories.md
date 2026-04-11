# Feedback Failure Categories — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-bucket failure classification (`intent`/`execution`/`info`) to negative feedback, stored on `FeedbackEntry` and collected via a redesigned `FeedbackWidget` panel.

**Architecture:** Add a nullable `category` field to `FeedbackEntry`, migrate the `feedback` SQLite table with an idempotent `ALTER TABLE`, plumb the field through `_store_feedback` and `_export_feedback_csv`. Rework the React widget so thumbs-down opens a panel with three required category pills and an optional textarea.

**Tech Stack:** Python, FastAPI, pydantic, aiosqlite, React/Next.js, TypeScript

---

### Task 1: Add `category` to `FeedbackEntry` model

**Files:**
- Modify: `teams/team5/backend/models.py` (`FeedbackEntry`)
- Modify: `teams/team5/backend/tests/test_models.py` (add `TestFeedbackEntryCategory`)

- [ ] **Step 1: Add failing test for valid category values**

In `teams/team5/backend/tests/test_models.py`, add the following at the end of the file:

```python
class TestFeedbackEntryCategory:
    def test_accepts_intent_category(self):
        entry = FeedbackEntry(
            session_id="s1",
            message_id="m1",
            rating="negative",
            query="Wat is borstkanker?",
            sources_tried=["kanker_nl"],
            category="intent",
        )
        assert entry.category == "intent"

    def test_accepts_execution_category(self):
        entry = FeedbackEntry(
            session_id="s1",
            message_id="m1",
            rating="negative",
            query="q",
            sources_tried=[],
            category="execution",
        )
        assert entry.category == "execution"

    def test_accepts_info_category(self):
        entry = FeedbackEntry(
            session_id="s1",
            message_id="m1",
            rating="negative",
            query="q",
            sources_tried=[],
            category="info",
        )
        assert entry.category == "info"

    def test_category_defaults_to_none(self):
        entry = FeedbackEntry(
            session_id="s1",
            message_id="m1",
            rating="positive",
            query="q",
            sources_tried=[],
        )
        assert entry.category is None

    def test_rejects_invalid_category(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(
                session_id="s1",
                message_id="m1",
                rating="negative",
                query="q",
                sources_tried=[],
                category="garbage",
            )
```

If `FeedbackEntry` and `ValidationError` aren't already imported at the top of the test file, add them. Look at the existing imports and add to the import block as needed:

```python
from pydantic import ValidationError
from models import FeedbackEntry
```

(Only add imports that aren't already present — check the top of `test_models.py` first.)

- [ ] **Step 2: Run the tests — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_models.py::TestFeedbackEntryCategory -v`
Expected: FAIL — `FeedbackEntry` has no `category` field; all five tests error with `ValidationError: Extra inputs are not permitted` or similar.

- [ ] **Step 3: Add `category` field to `FeedbackEntry`**

In `teams/team5/backend/models.py`, locate the `FeedbackEntry` class:

```python
class FeedbackEntry(BaseModel):
    session_id: str
    message_id: str
    rating: Literal["positive", "negative"]
    comment: Optional[str] = None
    query: str
    sources_tried: list[str]
    profile: Optional[str] = None
    timestamp: Optional[datetime] = None
```

Replace it with:

```python
class FeedbackEntry(BaseModel):
    session_id: str
    message_id: str
    rating: Literal["positive", "negative"]
    comment: Optional[str] = None
    query: str
    sources_tried: list[str]
    profile: Optional[str] = None
    category: Optional[Literal["intent", "execution", "info"]] = None
    timestamp: Optional[datetime] = None
```

- [ ] **Step 4: Run the tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_models.py::TestFeedbackEntryCategory -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add teams/team5/backend/models.py teams/team5/backend/tests/test_models.py
git commit -m "feat(models): add category field to FeedbackEntry"
```

---

### Task 2: Migrate `feedback` table with an idempotent ALTER TABLE

**Files:**
- Modify: `teams/team5/backend/main.py` (`_ensure_feedback_table`)
- Modify: `teams/team5/backend/tests/test_api.py` (add idempotency test)

- [ ] **Step 1: Write failing test for schema migration**

In `teams/team5/backend/tests/test_api.py`, add this new test class at the end of the file (after `TestChatStreamEndpoint`):

```python
class TestFeedbackSchemaMigration:
    @pytest.mark.asyncio
    async def test_ensure_feedback_table_adds_category_column(self, tmp_path):
        """_ensure_feedback_table must add the category column on an existing table
        that was created without it (simulates upgrading an old database)."""
        import aiosqlite
        from main import _ensure_feedback_table

        db_path = str(tmp_path / "legacy.db")

        # Create the legacy schema (no category column)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE feedback (
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

        # Run the migration
        await _ensure_feedback_table(db_path)

        # Verify the column now exists
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("PRAGMA table_info(feedback)") as cursor:
                cols = [row[1] for row in await cursor.fetchall()]

        assert "category" in cols

    @pytest.mark.asyncio
    async def test_ensure_feedback_table_is_idempotent(self, tmp_path):
        """Running _ensure_feedback_table twice on the same database must not raise."""
        from main import _ensure_feedback_table

        db_path = str(tmp_path / "idempotent.db")
        await _ensure_feedback_table(db_path)
        # Second call should be a no-op, not a failure
        await _ensure_feedback_table(db_path)
```

- [ ] **Step 2: Run the tests — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackSchemaMigration -v`
Expected: `test_ensure_feedback_table_adds_category_column` FAILS because the migration doesn't exist yet. `test_ensure_feedback_table_is_idempotent` may currently PASS — that's fine; it will keep passing after the change.

- [ ] **Step 3: Add the idempotent ALTER TABLE**

In `teams/team5/backend/main.py`, locate `_ensure_feedback_table`:

```python
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
```

Replace it with:

```python
async def _ensure_feedback_table(db_path: str) -> None:
    """Create the feedback table if it does not exist, and run migrations."""
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
                category TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )
        # Idempotent migration for pre-existing databases that lack `category`.
        try:
            await db.execute("ALTER TABLE feedback ADD COLUMN category TEXT")
        except aiosqlite.OperationalError:
            # Column already exists — fresh database or previous migration ran.
            pass
        await db.commit()
```

- [ ] **Step 4: Run the migration tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackSchemaMigration -v`
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add teams/team5/backend/main.py teams/team5/backend/tests/test_api.py
git commit -m "feat(feedback): idempotent schema migration for category column"
```

---

### Task 3: Persist `category` in `_store_feedback`

**Files:**
- Modify: `teams/team5/backend/main.py` (`_store_feedback`)
- Modify: `teams/team5/backend/tests/test_api.py` (add persistence test)

- [ ] **Step 1: Write failing test for category persistence**

Add to the `TestFeedbackEndpoint` class in `teams/team5/backend/tests/test_api.py` (after `test_feedback_export_returns_csv`):

```python
    @pytest.mark.asyncio
    async def test_feedback_persists_category(self, tmp_path):
        """Negative feedback with a category should persist it to the database."""
        import aiosqlite

        db_path = str(tmp_path / "test_feedback.db")
        with patch("main.FEEDBACK_DB_PATH", db_path):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "session_id": "sess-cat",
                    "message_id": "msg-cat",
                    "rating": "negative",
                    "category": "intent",
                    "comment": "verkeerd begrepen",
                    "query": "Wat is borstkanker?",
                    "sources_tried": ["kanker_nl"],
                }
                response = await client.post("/api/feedback", json=payload)

            assert response.status_code == 201

        # Read back from the database to confirm persistence
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT category FROM feedback WHERE session_id = ?",
                ("sess-cat",),
            ) as cursor:
                row = await cursor.fetchone()

        assert row is not None
        assert row["category"] == "intent"

    @pytest.mark.asyncio
    async def test_feedback_rejects_invalid_category(self, tmp_path):
        """Invalid category values should 422."""
        db_path = str(tmp_path / "test_feedback.db")
        with patch("main.FEEDBACK_DB_PATH", db_path):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "session_id": "sess-bad",
                    "message_id": "msg-bad",
                    "rating": "negative",
                    "category": "garbage",
                    "query": "q",
                    "sources_tried": [],
                }
                response = await client.post("/api/feedback", json=payload)

        assert response.status_code == 422
```

- [ ] **Step 2: Run the tests — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackEndpoint::test_feedback_persists_category -v`
Expected: FAIL — the INSERT in `_store_feedback` doesn't write the `category` column, so the round-trip fetches NULL.

(The `test_feedback_rejects_invalid_category` test should already PASS because pydantic validation from Task 1 rejects the invalid value before it reaches the endpoint.)

- [ ] **Step 3: Update `_store_feedback` to persist category**

In `teams/team5/backend/main.py`, locate `_store_feedback`:

```python
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
```

Replace it with:

```python
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
                 query, sources_tried, profile, category, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                entry.category,
                timestamp,
            ),
        )
        await db.commit()

    return feedback_id
```

- [ ] **Step 4: Run the tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackEndpoint -v`
Expected: All feedback endpoint tests PASS (including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add teams/team5/backend/main.py teams/team5/backend/tests/test_api.py
git commit -m "feat(feedback): persist category in _store_feedback"
```

---

### Task 4: Export `category` in the CSV

**Files:**
- Modify: `teams/team5/backend/main.py` (`_export_feedback_csv`)
- Modify: `teams/team5/backend/tests/test_api.py` (add export test)

- [ ] **Step 1: Write failing test for CSV export**

Add to the `TestFeedbackEndpoint` class in `teams/team5/backend/tests/test_api.py`:

```python
    @pytest.mark.asyncio
    async def test_feedback_export_includes_category(self, tmp_path):
        """CSV export should include the category column and the stored value."""
        db_path = str(tmp_path / "test_feedback.db")
        with patch("main.FEEDBACK_DB_PATH", db_path):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Store one entry with a category
                await client.post("/api/feedback", json={
                    "session_id": "sess-exp",
                    "message_id": "msg-exp",
                    "rating": "negative",
                    "category": "execution",
                    "query": "q",
                    "sources_tried": ["publications"],
                })
                response = await client.get("/api/feedback/export")

            assert response.status_code == 200
            body = response.text
            assert "category" in body  # header present
            assert "execution" in body  # value present
```

- [ ] **Step 2: Run the test — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackEndpoint::test_feedback_export_includes_category -v`
Expected: FAIL — the CSV header and row don't include `category`.

- [ ] **Step 3: Update `_export_feedback_csv`**

In `teams/team5/backend/main.py`, locate `_export_feedback_csv`:

```python
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
```

Replace it with:

```python
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "message_id",
            "rating",
            "category",
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
                row["category"] if "category" in row.keys() else None,
                row["comment"],
                row["query"],
                row["sources_tried"],
                row["profile"],
                row["timestamp"],
            ]
        )

    return output.getvalue()
```

(The `row["category"] if "category" in row.keys() else None` guard protects against legacy databases where the `SELECT *` wouldn't return the column — with the migration in Task 2 it'll always be present, but the guard is cheap insurance.)

- [ ] **Step 4: Run the tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_api.py::TestFeedbackEndpoint -v`
Expected: All feedback tests PASS.

- [ ] **Step 5: Run the full backend test suite**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add teams/team5/backend/main.py teams/team5/backend/tests/test_api.py
git commit -m "feat(feedback): include category in CSV export"
```

---

### Task 5: Add `category` to the frontend `FeedbackRequest` type

**Files:**
- Modify: `teams/team5/frontend/lib/types.ts` (`FeedbackRequest`)

- [ ] **Step 1: Add the category field to `FeedbackRequest`**

In `teams/team5/frontend/lib/types.ts`, locate:

```typescript
export interface FeedbackRequest {
  session_id: string;
  message_id: string;
  rating: "positive" | "negative";
  comment?: string;
  query: string;
  sources_tried: string[];
}
```

Replace it with:

```typescript
export type FeedbackCategory = "intent" | "execution" | "info";

export interface FeedbackRequest {
  session_id: string;
  message_id: string;
  rating: "positive" | "negative";
  comment?: string;
  query: string;
  sources_tried: string[];
  category?: FeedbackCategory;
}
```

- [ ] **Step 2: Type-check the frontend**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/frontend/lib/types.ts
git commit -m "frontend: add FeedbackCategory type"
```

---

### Task 6: Rework `FeedbackWidget` to collect the category

**Files:**
- Modify: `teams/team5/frontend/components/FeedbackWidget.tsx` (full rewrite of the return JSX and state)

- [ ] **Step 1: Replace the widget with the new flow**

Replace the entire contents of `teams/team5/frontend/components/FeedbackWidget.tsx` with:

```typescript
// frontend/components/FeedbackWidget.tsx

"use client";

import React, { useState } from "react";
import { submitFeedback } from "@/lib/chat-client";
import type { FeedbackCategory } from "@/lib/types";

interface FeedbackWidgetProps {
  sessionId: string;
  messageId: string;
  query: string;
  sourcesTried: string[];
}

const CATEGORY_OPTIONS: { value: FeedbackCategory; label: string }[] = [
  {
    value: "intent",
    label: "U heeft mijn vraag verkeerd begrepen",
  },
  {
    value: "execution",
    label: "De juiste vraag, maar op de verkeerde plek gezocht",
  },
  {
    value: "info",
    label: "De informatie zelf klopt niet",
  },
];

export default function FeedbackWidget({
  sessionId,
  messageId,
  query,
  sourcesTried,
}: FeedbackWidgetProps) {
  const [rating, setRating] = useState<"positive" | "negative" | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleThumbsUp = async () => {
    setRating("positive");
    setSubmitted(true);
    try {
      await submitFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating: "positive",
        query,
        sources_tried: sourcesTried,
      });
    } catch {
      // Silently fail feedback — non-critical
    }
  };

  const handleThumbsDown = () => {
    setRating("negative");
    setShowPanel(true);
  };

  const handleSubmitNegative = async () => {
    if (!category) return;
    setSubmitted(true);
    try {
      await submitFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating: "negative",
        category,
        comment: comment.trim() || undefined,
        query,
        sources_tried: sourcesTried,
      });
    } catch {
      // Silently fail
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <button
          onClick={handleThumbsUp}
          disabled={rating !== null}
          className={`p-1 rounded transition-colors ${
            rating === "positive"
              ? "text-green-600"
              : "text-gray-300 hover:text-gray-500"
          } disabled:cursor-default`}
          aria-label="Positieve feedback"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
          </svg>
        </button>

        <button
          onClick={handleThumbsDown}
          disabled={rating !== null}
          className={`p-1 rounded transition-colors ${
            rating === "negative"
              ? "text-red-500"
              : "text-gray-300 hover:text-gray-500"
          } disabled:cursor-default`}
          aria-label="Negatieve feedback"
        >
          <svg
            className="w-4 h-4 rotate-180"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
          </svg>
        </button>

        {submitted && (
          <span className="text-xs text-green-600 ml-1">
            Bedankt voor uw feedback!
          </span>
        )}
      </div>

      {showPanel && !submitted && (
        <div className="flex flex-col gap-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-xs font-medium text-gray-700">Wat ging er mis?</p>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setCategory(opt.value)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  category === opt.value
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Kunt u dit toelichten? (optioneel)"
            rows={2}
            className="text-xs px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
          />
          <button
            onClick={handleSubmitNegative}
            disabled={!category}
            className="self-end text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Verstuur
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check the frontend**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/frontend/components/FeedbackWidget.tsx
git commit -m "frontend(feedback): collect failure category on thumbs-down"
```

---

### Task 7: Smoke check

**Files:** None (verification only).

- [ ] **Step 1: Full backend test suite**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest -v`
Expected: All tests PASS.

- [ ] **Step 2: Frontend type check**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Rebuild and restart the backend container**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5 && docker compose build backend && docker compose up -d --force-recreate backend`
Expected: Container rebuilds and starts cleanly.

- [ ] **Step 4: End-to-end check via curl**

Wait for the backend to become healthy (poll `/api/health` until 200), then run:

```bash
curl -s -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "smoke-1",
    "message_id": "smoke-msg-1",
    "rating": "negative",
    "category": "intent",
    "comment": "Test from smoke check",
    "query": "test",
    "sources_tried": ["kanker_nl"]
  }'
```

Expected: HTTP 201 with `{"id": "..."}`.

Then:

```bash
curl -s http://localhost:8000/api/feedback/export | head -5
```

Expected: CSV header contains `category`, and at least one row contains `intent`.
