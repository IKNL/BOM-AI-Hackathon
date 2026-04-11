# Search Query Rewrite — Design Spec

**Date**: 2026-04-11
**Status**: Approved

## Problem

`vraag_tekst` is produced by the LangGraph analyze step as an LLM paraphrase of
the user's question. It often contains third-person meta-framing such as
*"De gebruiker zoekt naar recente innovaties en bevindingen in het
kankeronderzoek"*. When this string is passed directly to the embedding model
as a semantic search query, the *"De gebruiker zoekt naar..."* prefix
pollutes the embedding and retrieval quality drops — often to zero hits on
otherwise well-covered topics.

## Goal

Produce a clean, natural-language `search_query` alongside the existing
`samenvatting`, `kankersoort`, and `vraag_type` fields, and use it as the
embedding query for every vector-search connector call.

## Scope

- Extend the existing `summarize_question` LLM call to also produce a
  `search_query` field. No new LLM call.
- Thread `search_query` from summarize → frontend → `/api/intake/search` →
  `search_and_format` → vector-search connectors.
- Update existing tests.

## Non-goals

- Multi-query retrieval or query expansion.
- Translating queries between languages.
- Rewriting queries inside the LangGraph analyze step.
- Backwards compatibility — `search_query` is a required field end-to-end.

## Design

### Data flow

```
User message
  → /api/intake/analyze (LangGraph)
      → vraag_tekst (may be paraphrased, used for display + NKR cancer_type)
  → /api/intake/summarize
      → { samenvatting, kankersoort, vraag_type, search_query }
  → /api/intake/search
      → search_and_format(..., search_query=search_query)
          → kanker_nl / publications connectors receive search_query as the
            embedding query
          → nkr_cijfers still receives vraag_tekst as cancer_type
```

### Components

#### `backend/models.py`
- Add `search_query: str` to `IntakeSummarizeResponse` (required).
- Add `search_query: str` to `IntakeSearchRequest` (required).

#### `backend/intake.py`

**`_SUMMARIZE_PROMPT_TEMPLATE`** — extend with a fourth instruction:

> 4. Schrijf een korte, natuurlijke zoekvraag (`search_query`) die geschikt
>    is voor semantische vectorzoekopdrachten. Gebruik ALLEEN de
>    onderliggende vraag (bijvoorbeeld: "welke recente innovaties zijn er in
>    het kankeronderzoek?"). Schrijf NOOIT meta-tekst zoals "de gebruiker
>    zoekt naar..." of "ik wil graag weten". Maximaal 15 woorden.

JSON output shape becomes:

```json
{
  "samenvatting": "...",
  "kankersoort": "..." | "geen",
  "vraag_type": "...",
  "search_query": "..."
}
```

**`summarize_question()`** — parse `search_query` from the JSON. If the LLM
omits it or returns empty, use `vraag_tekst` as the value (safety net against
LLM drift, not a "backwards compat" path). No optionality on the return type.

**`search_and_format()`** — signature gains `search_query: str`. In the
connector loop, set `query_params["query"] = search_query` for the
`kanker_nl` and `publications` connectors. `vraag_tekst` is still used as
`cancer_type` for `nkr_cijfers` and passed to the display template.

#### `backend/main.py`
`/api/intake/search` request validation gains the `search_query` field.
Threads it into `search_and_format`.

#### `frontend/lib/types.ts`
Add `search_query: string` to `IntakeSummarizeResponse` and to the
`searchAndStream` request type.

#### `frontend/lib/intake-client.ts`
`searchAndStream` request body includes `search_query`.

#### Frontend state (chat page)
Wherever `summarizeQuestion()` result is stored, also store `search_query`
and pass it to `searchAndStream()`.

### Testing

- **Unit — `summarize_question` parses `search_query`**: mock LLM returns
  JSON containing `search_query`, assert returned object carries it.
- **Unit — `summarize_question` safety net**: mock LLM returns JSON
  without `search_query`, assert returned object uses `vraag_tekst`.
- **Unit — `search_and_format` uses `search_query`**: mock connectors,
  assert that `kanker_nl` and `publications` are called with
  `query=search_query`, not `query=vraag_tekst`.
- **Existing tests**: update any call site of `summarize_question` or
  `search_and_format` that doesn't pass `search_query`.

## Files to touch

- `teams/team5/backend/models.py`
- `teams/team5/backend/intake.py`
- `teams/team5/backend/main.py`
- `teams/team5/backend/tests/test_intake.py`
- `teams/team5/frontend/lib/types.ts`
- `teams/team5/frontend/lib/intake-client.ts`
- `teams/team5/frontend/app/page.tsx` (chat page state — stores
  `summarizeQuestion` result and passes it to `searchAndStream`)
