# Search Query Rewrite — Design Spec

**Date**: 2026-04-11
**Status**: Approved (revised after discovering the real UX flow)

## Problem

`vraag_tekst` is produced by the LangGraph intake flow (`intake_graph.py`,
the `vraag` step) as an LLM paraphrase of the user's question. It often
contains third-person meta-framing such as *"De gebruiker zoekt naar recente
innovaties en bevindingen in het kankeronderzoek"*. When this string is
passed directly to the embedding model as a semantic search query, the
*"De gebruiker zoekt naar..."* prefix pollutes the embedding and retrieval
quality drops — often to zero hits on otherwise well-covered topics.

## Goal

Produce a clean, natural-language `search_query` alongside the existing
`samenvatting`, `kankersoort`, and `vraag_type` fields, and use it as the
embedding query for every vector-search connector call.

## Scope

- Extend the LangGraph `vraag` step in `intake_graph.py` to also produce a
  `search_query` field. No new LLM call — it's added to the existing JSON
  output of that step.
- Persist `search_query` on `GegevensModel` so it survives through session
  storage and is available to the frontend.
- Thread `search_query` from frontend → `/api/intake/search` →
  `search_and_format` → vector-search connectors.
- Update the legacy `summarize_question` function and its tests to match the
  new shape (it shares the `IntakeSummarizeResponse` model with the LangGraph
  path; keeping the shapes aligned avoids schema drift).

## Non-goals

- Multi-query retrieval or query expansion.
- Translating queries between languages.
- Removing the legacy `/api/intake/summarize` endpoint.
- Backwards compatibility — `search_query` is a required field end-to-end.

## Design

### Data flow

```
User message
  → /api/intake/analyze → run_intake_step (intake_graph.py)
      → "vraag" step LLM call produces
        { vraag_tekst, kankersoort, vraag_type, samenvatting, search_query }
      → stored in GegevensModel, persisted to session, returned to frontend
  → /api/intake/search (with gegevens.search_query in the payload)
      → search_and_format(..., search_query=search_query)
          → kanker_nl / publications connectors embed search_query
          → nkr_cijfers still receives vraag_tekst for cancer_type
```

### Components

#### `backend/models.py`
- Add `search_query: str | None` to `GegevensModel` (nullable because it's
  populated partway through the conversation).
- Add `search_query: str` to `IntakeSearchRequest` (required — by the time
  we hit /api/intake/search, the `vraag` step has run).
- Add `search_query: str` to `IntakeSummarizeResponse` (required, for the
  legacy `summarize_question` path which shares the model).

#### `backend/intake_graph.py`

**`STEP_PROMPTS["vraag"]`** — extend with a fifth instruction and update the
JSON output shape:

> 5. Schrijf een korte, natuurlijke zoekvraag (`search_query`) die geschikt
>    is voor semantische vectorzoekopdrachten. Gebruik ALLEEN de
>    onderliggende vraag (bijvoorbeeld: "welke recente innovaties zijn er in
>    het kankeronderzoek?"). Schrijf NOOIT meta-tekst zoals "de gebruiker
>    zoekt naar..." of "ik wil graag weten". Maximaal 15 woorden.

Updated JSON shape:

```json
{
  "vraag_tekst": "...",
  "kankersoort": "..." | null,
  "vraag_type": "...",
  "samenvatting": "...",
  "search_query": "...",
  "scope": "in_scope" | "off_topic",
  "bot_message": "..."
}
```

**`_run_vraag_step()`** — parse `search_query` from the LLM JSON and store
it on `g["search_query"]`. If the LLM omits the field or returns empty,
fall back to `vraag_tekst` so the downstream search always has something
usable (this is a safety net against LLM drift, not backwards compat).

#### `backend/intake.py`

**`summarize_question()`** — update the prompt template with the same
fifth instruction, parse `search_query` from the JSON, and include it in
the returned `IntakeSummarizeResponse`. Safety-net fallback to `vraag_tekst`
if the LLM omits it.

**`search_and_format()`** — signature gains `search_query: str` (required).
In the connector loop, set `query_params["query"] = search_query` for the
`kanker_nl` and `publications` connectors. `vraag_tekst` continues to feed
`nkr_cijfers` `cancer_type` and the display template.

#### `backend/main.py`
- `IntakeSearchRequest` gains `search_query`, threaded into
  `search_and_format`.

#### `frontend/lib/types.ts`
- Add `search_query: string | null` to `GegevensModel`.
- Add `search_query: string` to `IntakeSummarizeResponse`.

#### `frontend/lib/intake-client.ts`
- `searchAndStream` request body includes `search_query`.

#### `frontend/app/page.tsx`
- `searchAndStream` call sends `search_query: g.search_query || g.vraag_tekst || ""`.
- Wherever `gegevens` state is initialised/reset, include `search_query: null`.

### Testing

- **Unit — `_run_vraag_step` parses `search_query`**: mock LLM returns JSON
  containing `search_query`, assert it's stored on the returned gegevens.
- **Unit — `_run_vraag_step` safety net**: mock LLM returns JSON without
  `search_query`, assert `search_query == vraag_tekst` on the returned
  gegevens.
- **Unit — `summarize_question` parses `search_query`**: mock LLM returns
  JSON containing it; assert on the returned `IntakeSummarizeResponse`.
- **Unit — `summarize_question` safety net**: mock LLM omits `search_query`;
  assert fallback to `vraag_tekst`.
- **Unit — `search_and_format` uses `search_query`**: mock connectors,
  assert that `kanker_nl` and `publications` are called with
  `query=search_query`, not `query=vraag_tekst`.
- **Existing tests**: update any call site of `summarize_question` or
  `search_and_format` to supply `search_query`.

## Files to touch

- `teams/team5/backend/models.py`
- `teams/team5/backend/intake_graph.py`
- `teams/team5/backend/intake.py`
- `teams/team5/backend/main.py`
- `teams/team5/backend/tests/test_intake.py`
- `teams/team5/backend/tests/test_intake_graph.py` (create if needed for
  `_run_vraag_step` coverage)
- `teams/team5/frontend/lib/types.ts`
- `teams/team5/frontend/lib/intake-client.ts`
- `teams/team5/frontend/app/page.tsx`
