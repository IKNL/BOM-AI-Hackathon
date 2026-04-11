# Feedback Failure Categories — Design Spec

**Date**: 2026-04-11
**Status**: Approved

## Problem

The current feedback widget lets a user give a thumbs up/down plus an
optional free-text "Informatie mist?" comment. That's enough to flag
broken answers, but it tells us nothing about *why* the answer was broken —
whether the system misread the user's intent, picked the wrong sources,
or returned wrong content. Without that classification the feedback log is
hard to triage or learn from.

## Goal

When a user gives negative feedback, collect a structured diagnosis of
what went wrong. Map the failure to one of three buckets that line up with
the RAG pipeline stages:

1. **intent** — the system misunderstood what the user wanted.
2. **execution** — the intent was understood, but the sources queried or
   the way they were queried was wrong.
3. **info** — the right sources were queried, but the returned content was
   wrong, irrelevant, or inaccurate.

## Scope

- Extend `FeedbackEntry` with a `category` field.
- Migrate the `feedback` SQLite table to carry the new column (idempotent
  `ALTER TABLE`).
- Rework the `FeedbackWidget` so thumbs-down opens a two-step panel with
  three category buttons (required) and an optional textarea.
- Remove the existing "Informatie mist?" inline link/input — the new panel
  replaces it.
- Include the new column in `/api/feedback/export` CSV output.

## Non-goals

- Admin dashboard changes. (CSV export is enough for hackathon triage.)
- Triage/routing logic that acts on category at runtime.
- Backwards-compatible migration of historical feedback rows (the column
  stays NULL for them).

## Design

### Data model

**`backend/models.py`** — add to `FeedbackEntry`:

```python
category: Literal["intent", "execution", "info"] | None = None
```

The field is nullable because:
- Positive feedback never sets it.
- Historical rows don't have it.
- Pydantic will 422 any invalid value.

### Storage

**`backend/main.py`**

- `_ensure_feedback_table()` — after the existing `CREATE TABLE IF NOT
  EXISTS`, run `ALTER TABLE feedback ADD COLUMN category TEXT` wrapped in a
  `try/except aiosqlite.OperationalError` so it's a no-op on subsequent
  startups.
- `_store_feedback()` — include `category` in the INSERT statement.
- `_export_feedback_csv()` — include `category` in the CSV header and row
  output.

### API

`/api/feedback` (POST) — no endpoint code changes. The `FeedbackEntry`
pydantic model picks up the new field automatically. Requests that omit
`category` still validate. Requests that include an invalid value return
422.

### Frontend

**`frontend/components/FeedbackWidget.tsx`** — new flow:

1. User sees the thumbs up / thumbs down buttons (unchanged styling).
2. **Thumbs up**: one-click, POSTs `{rating: "positive"}` immediately. Done.
3. **Thumbs down**: opens a panel below the thumbs containing:
   - Prompt: *"Wat ging er mis?"*
   - Three pill buttons, exactly one selectable:
     - *"U heeft mijn vraag verkeerd begrepen"* → value `intent`
     - *"De juiste vraag, maar op de verkeerde plek gezocht"* → value
       `execution`
     - *"De informatie zelf klopt niet"* → value `info`
   - Optional textarea: *"Kunt u dit toelichten? (optioneel)"*
   - "Verstuur" button, disabled until a category is selected.
4. On submit, POSTs `{rating: "negative", category, comment}`.

The existing "Informatie mist?" separate link and inline input are removed —
the new panel replaces them entirely. One feedback path.

**`frontend/lib/types.ts`** — add to `FeedbackRequest`:

```typescript
category?: "intent" | "execution" | "info";
```

**`frontend/lib/chat-client.ts`** — `submitFeedback` request body
passes the optional `category` through.

### Testing

Backend unit tests (new in `tests/test_models.py` and
`tests/test_api.py`):

- `FeedbackEntry` accepts valid category values (`"intent"`,
  `"execution"`, `"info"`).
- `FeedbackEntry` rejects an invalid category with `ValidationError`.
- `FeedbackEntry` accepts `category=None` and missing field.
- `_store_feedback()` persists category correctly for a row that has it.
- `_store_feedback()` persists NULL for a row that omits it.
- `_export_feedback_csv()` output contains the `category` header and the
  stored value.
- `_ensure_feedback_table()` is idempotent — running it twice on the same
  database doesn't raise.

Frontend tests are out of scope (no existing test setup for components).

## Files to touch

- `teams/team5/backend/models.py`
- `teams/team5/backend/main.py`
- `teams/team5/backend/tests/test_models.py`
- `teams/team5/backend/tests/test_api.py`
- `teams/team5/frontend/components/FeedbackWidget.tsx`
- `teams/team5/frontend/lib/types.ts`
- `teams/team5/frontend/lib/chat-client.ts`
