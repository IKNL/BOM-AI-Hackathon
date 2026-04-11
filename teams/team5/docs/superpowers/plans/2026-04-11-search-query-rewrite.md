# Search Query Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a clean, embedding-friendly `search_query` inside the LangGraph `vraag` step and thread it end-to-end so vector-search connectors receive a topical query instead of LLM-paraphrased meta-text.

**Architecture:** The existing `vraag` step LLM call in `intake_graph.py` gains a fifth output field (`search_query`). It flows into `GegevensModel`, through the `/api/intake/search` request, into `search_and_format`, and is used as the `query` param for `kanker_nl` and `publications` connectors. `vraag_tekst` stays for display and NKR cancer_type.

**Tech Stack:** LangGraph, pydantic, FastAPI, Next.js/TypeScript

---

### Task 1: Add `search_query` to the backend data model

**Files:**
- Modify: `teams/team5/backend/models.py` (`GegevensModel`, `IntakeSummarizeResponse`, `IntakeSearchRequest`)

- [ ] **Step 1: Add `search_query` to `GegevensModel`**

In `teams/team5/backend/models.py`, change the `GegevensModel` class. Replace:

```python
class GegevensModel(BaseModel):
    """Intake data model — drives the structured intake flow."""
    ai_bekendheid: Literal["niet_bekend", "enigszins", "erg_bekend"] | None = None
    gebruiker_type: Literal[
        "patient", "publiek", "zorgverlener", "student",
        "beleidsmaker", "onderzoeker", "journalist", "anders"
    ] | None = None
    vraag_tekst: str | None = None
    kankersoort: str | None = None
    vraag_type: str | None = None
    samenvatting: str | None = None
    bevestigd: bool = False
```

with:

```python
class GegevensModel(BaseModel):
    """Intake data model — drives the structured intake flow."""
    ai_bekendheid: Literal["niet_bekend", "enigszins", "erg_bekend"] | None = None
    gebruiker_type: Literal[
        "patient", "publiek", "zorgverlener", "student",
        "beleidsmaker", "onderzoeker", "journalist", "anders"
    ] | None = None
    vraag_tekst: str | None = None
    kankersoort: str | None = None
    vraag_type: str | None = None
    samenvatting: str | None = None
    search_query: str | None = None
    bevestigd: bool = False
```

- [ ] **Step 2: Add `search_query` to `IntakeSummarizeResponse`**

Replace:

```python
class IntakeSummarizeResponse(BaseModel):
    """Response from /api/intake/summarize."""
    samenvatting: str
    kankersoort: str  # "geen" if not mentioned
    vraag_type: str   # patient_info | cijfers | regionaal | onderzoek | breed
```

with:

```python
class IntakeSummarizeResponse(BaseModel):
    """Response from /api/intake/summarize."""
    samenvatting: str
    kankersoort: str  # "geen" if not mentioned
    vraag_type: str   # patient_info | cijfers | regionaal | onderzoek | breed
    search_query: str  # clean topical query for vector search
```

- [ ] **Step 3: Add `search_query` to `IntakeSearchRequest`**

Replace:

```python
class IntakeSearchRequest(BaseModel):
    """Request body for /api/intake/search."""
    ai_bekendheid: Literal["niet_bekend", "enigszins", "erg_bekend"]
    gebruiker_type: Literal[
        "patient", "publiek", "zorgverlener", "student",
        "beleidsmaker", "onderzoeker", "journalist", "anders"
    ]
    vraag_tekst: str
    kankersoort: str | None = None
    vraag_type: str | None = None
    samenvatting: str
```

with:

```python
class IntakeSearchRequest(BaseModel):
    """Request body for /api/intake/search."""
    ai_bekendheid: Literal["niet_bekend", "enigszins", "erg_bekend"]
    gebruiker_type: Literal[
        "patient", "publiek", "zorgverlener", "student",
        "beleidsmaker", "onderzoeker", "journalist", "anders"
    ]
    vraag_tekst: str
    kankersoort: str | None = None
    vraag_type: str | None = None
    samenvatting: str
    search_query: str
```

- [ ] **Step 4: Commit**

```bash
git add teams/team5/backend/models.py
git commit -m "models: add search_query field to intake + search models"
```

---

### Task 2: Write failing test for LangGraph `vraag` step `search_query` parsing

**Files:**
- Create: `teams/team5/backend/tests/test_intake_graph.py`

- [ ] **Step 1: Create the test file**

Create `teams/team5/backend/tests/test_intake_graph.py` with:

```python
"""Tests for the LangGraph intake flow — focused on vraag step search_query."""

import json
import pytest
from unittest.mock import AsyncMock, patch


class TestVraagStepSearchQuery:
    @pytest.mark.asyncio
    async def test_vraag_node_parses_search_query(self):
        from intake_graph import vraag_node

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "vraag_tekst": "De gebruiker zoekt naar recente innovaties in kankeronderzoek",
                        "kankersoort": None,
                        "vraag_type": "onderzoek",
                        "samenvatting": "U zoekt informatie over recente innovaties in kankeronderzoek.",
                        "search_query": "welke recente innovaties zijn er in het kankeronderzoek",
                        "scope": "in_scope",
                        "bot_message": "Als ik het goed begrijp zoekt u informatie over...",
                    })
                )
            )
        ]

        state = {
            "message": "Wat zijn recente innovaties in kankeronderzoek?",
            "gegevens": {
                "ai_bekendheid": "enigszins",
                "gebruiker_type": "onderzoeker",
                "vraag_tekst": None,
                "kankersoort": None,
                "vraag_type": None,
                "samenvatting": None,
                "search_query": None,
                "bevestigd": False,
            },
            "model": "test-model",
        }

        with patch("intake_graph.litellm.acompletion", return_value=mock_response):
            result = await vraag_node(state)

        assert result["gegevens"]["search_query"] == "welke recente innovaties zijn er in het kankeronderzoek"

    @pytest.mark.asyncio
    async def test_vraag_node_falls_back_to_vraag_tekst_when_search_query_missing(self):
        from intake_graph import vraag_node

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "vraag_tekst": "Wat is borstkanker?",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "scope": "in_scope",
                        "bot_message": "Klopt dit?",
                    })
                )
            )
        ]

        state = {
            "message": "Wat is borstkanker?",
            "gegevens": {
                "ai_bekendheid": "enigszins",
                "gebruiker_type": "patient",
                "vraag_tekst": None,
                "kankersoort": None,
                "vraag_type": None,
                "samenvatting": None,
                "search_query": None,
                "bevestigd": False,
            },
            "model": "test-model",
        }

        with patch("intake_graph.litellm.acompletion", return_value=mock_response):
            result = await vraag_node(state)

        assert result["gegevens"]["search_query"] == "Wat is borstkanker?"

    @pytest.mark.asyncio
    async def test_vraag_node_falls_back_when_search_query_is_empty_string(self):
        from intake_graph import vraag_node

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "vraag_tekst": "Hoeveel mensen krijgen longkanker?",
                        "kankersoort": "longkanker",
                        "vraag_type": "cijfers",
                        "samenvatting": "U zoekt cijfers over longkanker.",
                        "search_query": "",
                        "scope": "in_scope",
                        "bot_message": "Klopt dit?",
                    })
                )
            )
        ]

        state = {
            "message": "Hoeveel mensen krijgen longkanker?",
            "gegevens": {
                "ai_bekendheid": "enigszins",
                "gebruiker_type": "publiek",
                "vraag_tekst": None,
                "kankersoort": None,
                "vraag_type": None,
                "samenvatting": None,
                "search_query": None,
                "bevestigd": False,
            },
            "model": "test-model",
        }

        with patch("intake_graph.litellm.acompletion", return_value=mock_response):
            result = await vraag_node(state)

        assert result["gegevens"]["search_query"] == "Hoeveel mensen krijgen longkanker?"
```

- [ ] **Step 2: Run the test — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake_graph.py -v`
Expected: FAIL — `vraag_node` doesn't set `search_query` yet.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/backend/tests/test_intake_graph.py
git commit -m "test: add failing tests for vraag step search_query parsing"
```

---

### Task 3: Implement `search_query` in the LangGraph `vraag` step

**Files:**
- Modify: `teams/team5/backend/intake_graph.py` (`STEP_PROMPTS["vraag"]` and `vraag_node`)

- [ ] **Step 1: Update the `vraag` step prompt**

In `teams/team5/backend/intake_graph.py`, locate `STEP_PROMPTS["vraag"]` (currently around lines 75-107). Replace the entire string value with:

```python
    "vraag": """Je bent een vriendelijke informatie-assistent. De gebruiker is een {gebruiker_type}.
Ze zijn {ai_bekendheid} bekend met AI.

Je ENIGE taak nu: begrijp wat de gebruiker wil weten.

De gebruiker zegt: "{message}"

Analyseer de vraag:
1. Wat is de kern van hun vraag? (vraag_tekst)
2. Wordt er een specifiek type aandoening genoemd? (kankersoort — alleen als EXPLICIET genoemd)
3. Welk type informatie zoeken ze? (vraag_type: patient_info / cijfers / regionaal / onderzoek / breed)
4. Schrijf een korte samenvatting (samenvatting)
5. Schrijf een korte, natuurlijke zoekvraag (search_query) die geschikt is voor semantische vectorzoekopdrachten. Gebruik ALLEEN de onderliggende vraag (bijvoorbeeld: "welke recente innovaties zijn er in het kankeronderzoek?"). Schrijf NOOIT meta-tekst zoals "de gebruiker zoekt naar..." of "ik wil graag weten". Maximaal 15 woorden.

Als de vraag DUIDELIJK genoeg is om mee te zoeken:
- Vul alle velden in
- Schrijf een bot_message die ALTIJD eindigt met een ja/nee-vraag, bijvoorbeeld:
  "Als ik het goed begrijp zoekt u informatie over [samenvatting]. Klopt dit?"
  of: "Ik denk dat u dit zoekt: [samenvatting]. Zal ik hiernaar zoeken?"
  De LAATSTE zin moet ALTIJD een vraag zijn die met ja of nee beantwoord kan worden.

Als de vraag ONDUIDELIJK is of te vaag:
- Vraag door met voorbeelden passend bij het gebruikerstype
- Laat samenvatting op null

Als de vraag BUITEN SCOPE valt (niet over kanker, gezondheid of IKNL-bronnen):
- Zet scope op "off_topic"
- Antwoord: "Ik begrijp dat u informatie zoekt over [onderwerp]. Helaas valt dit buiten mijn expertise. Ik kan u helpen met vragen over kanker en aanverwante gezondheidsonderwerpen. U kunt ook contact opnemen met IKNL voor verdere hulp."
- Laat alle andere velden op null

Antwoord ALLEEN in JSON:
{{"vraag_tekst": "..." of null, "kankersoort": "..." of null, "vraag_type": "..." of null, "samenvatting": "..." of null, "search_query": "..." of null, "scope": "in_scope" of "off_topic", "bot_message": "..."}}

TOON: {tone}. STIJL: {style}""",
```

- [ ] **Step 2: Update `vraag_node` to parse `search_query`**

Locate `vraag_node` in the same file (currently around lines 242-268). Replace the block:

```python
    if result.get("vraag_tekst"):
        g["vraag_tekst"] = result["vraag_tekst"]
    if result.get("kankersoort") and result["kankersoort"] not in ("geen", "null", ""):
        g["kankersoort"] = result["kankersoort"]
    if result.get("vraag_type"):
        g["vraag_type"] = result["vraag_type"]
    if result.get("samenvatting"):
        g["samenvatting"] = result["samenvatting"]

    return {**state, "gegevens": g, "bot_message": result.get("bot_message", ""), "off_topic": False}
```

with:

```python
    if result.get("vraag_tekst"):
        g["vraag_tekst"] = result["vraag_tekst"]
    if result.get("kankersoort") and result["kankersoort"] not in ("geen", "null", ""):
        g["kankersoort"] = result["kankersoort"]
    if result.get("vraag_type"):
        g["vraag_type"] = result["vraag_type"]
    if result.get("samenvatting"):
        g["samenvatting"] = result["samenvatting"]

    # Safety net against LLM drift: search_query must never be empty when
    # we have a vraag_tekst, so fall back to vraag_tekst if missing/empty.
    raw_search_query = (result.get("search_query") or "").strip()
    if raw_search_query:
        g["search_query"] = raw_search_query
    elif g.get("vraag_tekst"):
        g["search_query"] = g["vraag_tekst"]

    return {**state, "gegevens": g, "bot_message": result.get("bot_message", ""), "off_topic": False}
```

- [ ] **Step 3: Run tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake_graph.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add teams/team5/backend/intake_graph.py
git commit -m "feat(intake): emit search_query from LangGraph vraag step"
```

---

### Task 4: Write failing test for `summarize_question` parsing `search_query`

**Files:**
- Modify: `teams/team5/backend/tests/test_intake.py` (update existing summarize tests)

- [ ] **Step 1: Update `test_returns_summarize_response`**

In `teams/team5/backend/tests/test_intake.py`, replace the existing `test_returns_summarize_response` method body:

```python
    @pytest.mark.asyncio
    async def test_returns_summarize_response(self):
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                    })
                )
            )
        ]

        with patch("intake.litellm.acompletion", return_value=mock_response):
            result = await summarize_question(
                gebruiker_type="patient",
                vraag_tekst="Wat is borstkanker?",
                model="test-model",
            )

        assert isinstance(result, IntakeSummarizeResponse)
        assert result.samenvatting == "U zoekt informatie over borstkanker."
        assert result.kankersoort == "borstkanker"
        assert result.vraag_type == "patient_info"
```

with:

```python
    @pytest.mark.asyncio
    async def test_returns_summarize_response(self):
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                        "search_query": "wat is borstkanker",
                    })
                )
            )
        ]

        with patch("intake.litellm.acompletion", return_value=mock_response):
            result = await summarize_question(
                gebruiker_type="patient",
                vraag_tekst="Wat is borstkanker?",
                model="test-model",
            )

        assert isinstance(result, IntakeSummarizeResponse)
        assert result.samenvatting == "U zoekt informatie over borstkanker."
        assert result.kankersoort == "borstkanker"
        assert result.vraag_type == "patient_info"
        assert result.search_query == "wat is borstkanker"

    @pytest.mark.asyncio
    async def test_search_query_falls_back_to_vraag_tekst_when_missing(self):
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                    })
                )
            )
        ]

        with patch("intake.litellm.acompletion", return_value=mock_response):
            result = await summarize_question(
                gebruiker_type="patient",
                vraag_tekst="Wat is borstkanker?",
                model="test-model",
            )

        assert result.search_query == "Wat is borstkanker?"
```

- [ ] **Step 2: Update `test_handles_geen_kankersoort` to include `search_query`**

Replace the mock JSON content in `test_handles_geen_kankersoort`:

```python
                    content=json.dumps({
                        "samenvatting": "U zoekt algemene informatie over kanker.",
                        "kankersoort": "geen",
                        "vraag_type": "breed",
                    })
```

with:

```python
                    content=json.dumps({
                        "samenvatting": "U zoekt algemene informatie over kanker.",
                        "kankersoort": "geen",
                        "vraag_type": "breed",
                        "search_query": "wat doet IKNL",
                    })
```

- [ ] **Step 3: Update `test_summarize_endpoint` to include `search_query`**

Replace the mock JSON content in `test_summarize_endpoint`:

```python
                    content=json.dumps({
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                    })
```

with:

```python
                    content=json.dumps({
                        "samenvatting": "U zoekt informatie over borstkanker.",
                        "kankersoort": "borstkanker",
                        "vraag_type": "patient_info",
                        "search_query": "wat is borstkanker",
                    })
```

And add a new assertion after the existing asserts:

```python
        assert resp.status_code == 200
        data = resp.json()
        assert "samenvatting" in data
        assert "kankersoort" in data
        assert "vraag_type" in data
        assert "search_query" in data
```

- [ ] **Step 4: Run the test — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake.py::TestSummarizeQuestion -v`
Expected: FAIL — `IntakeSummarizeResponse` doesn't populate `search_query` from the LLM response yet.

- [ ] **Step 5: Commit**

```bash
git add teams/team5/backend/tests/test_intake.py
git commit -m "test: update summarize_question tests for search_query field"
```

---

### Task 5: Implement `search_query` in `summarize_question`

**Files:**
- Modify: `teams/team5/backend/intake.py` (`_SUMMARIZE_PROMPT_TEMPLATE` and `summarize_question`)

- [ ] **Step 1: Update `_SUMMARIZE_PROMPT_TEMPLATE`**

In `teams/team5/backend/intake.py`, locate `_SUMMARIZE_PROMPT_TEMPLATE` (currently around line 176). Replace the entire template value with:

```python
_SUMMARIZE_PROMPT_TEMPLATE = """Je bent een intake-assistent. De gebruiker heeft de volgende informatie gegeven:
- Type gebruiker: {gebruiker_type}
- Vraag: {vraag_tekst}

Doe vier dingen:
1. Schrijf een korte, natuurlijke samenvatting van wat de gebruiker zoekt (max 2 zinnen).
2. Als de gebruiker een specifiek type kanker noemt, geef die naam terug als "kankersoort". Zo niet, antwoord "geen". Vraag NOOIT zelf naar een kankersoort.
3. Classificeer welk type informatie de gebruiker zoekt als "vraag_type". Kies uit:
   - "patient_info" — algemene informatie, symptomen, behandeling, leven met kanker
   - "cijfers" — statistieken, incidentie, overleving, prevalentie
   - "regionaal" — regionale verschillen, gebiedsvergelijking
   - "onderzoek" — wetenschappelijke publicaties, rapporten, studies
   - "breed" — combinatie of onduidelijk
4. Schrijf een korte, natuurlijke zoekvraag (search_query) die geschikt is voor semantische vectorzoekopdrachten. Gebruik ALLEEN de onderliggende vraag (bijvoorbeeld: "welke recente innovaties zijn er in het kankeronderzoek?"). Schrijf NOOIT meta-tekst zoals "de gebruiker zoekt naar..." of "ik wil graag weten". Maximaal 15 woorden.

Antwoord in JSON:
{{"samenvatting": "...", "kankersoort": "..." of "geen", "vraag_type": "...", "search_query": "..."}}"""
```

- [ ] **Step 2: Update `summarize_question` to populate `search_query`**

Locate `summarize_question` in the same file. Replace the parsing block:

```python
    try:
        parsed = json.loads(raw)
        return IntakeSummarizeResponse(
            samenvatting=parsed.get("samenvatting", vraag_tekst),
            kankersoort=parsed.get("kankersoort", "geen"),
            vraag_type=parsed.get("vraag_type", "breed"),
        )
    except (json.JSONDecodeError, KeyError):
        logger.warning("LLM returned non-JSON for summarize: %s", raw[:200])
        return IntakeSummarizeResponse(
            samenvatting=vraag_tekst,
            kankersoort="geen",
            vraag_type="breed",
        )
```

with:

```python
    try:
        parsed = json.loads(raw)
        raw_search_query = (parsed.get("search_query") or "").strip()
        return IntakeSummarizeResponse(
            samenvatting=parsed.get("samenvatting", vraag_tekst),
            kankersoort=parsed.get("kankersoort", "geen"),
            vraag_type=parsed.get("vraag_type", "breed"),
            search_query=raw_search_query or vraag_tekst,
        )
    except (json.JSONDecodeError, KeyError):
        logger.warning("LLM returned non-JSON for summarize: %s", raw[:200])
        return IntakeSummarizeResponse(
            samenvatting=vraag_tekst,
            kankersoort="geen",
            vraag_type="breed",
            search_query=vraag_tekst,
        )
```

Also update the exception path that returns early when `litellm.acompletion` itself fails (in the same function). Replace:

```python
    except Exception as exc:
        logger.exception("LLM summarize call failed")
        return IntakeSummarizeResponse(
            samenvatting=vraag_tekst,
            kankersoort="geen",
            vraag_type="breed",
        )
```

with:

```python
    except Exception as exc:
        logger.exception("LLM summarize call failed")
        return IntakeSummarizeResponse(
            samenvatting=vraag_tekst,
            kankersoort="geen",
            vraag_type="breed",
            search_query=vraag_tekst,
        )
```

- [ ] **Step 3: Run tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake.py::TestSummarizeQuestion tests/test_intake.py::TestIntakeEndpoints -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add teams/team5/backend/intake.py
git commit -m "feat(intake): emit search_query from summarize_question LLM call"
```

---

### Task 6: Write failing test for `search_and_format` using `search_query`

**Files:**
- Modify: `teams/team5/backend/tests/test_intake.py` (`TestSearchAndFormat`)

- [ ] **Step 1: Replace `test_returns_sse_events` and add a new test**

In `teams/team5/backend/tests/test_intake.py`, replace the existing `test_returns_sse_events` method with these two tests:

```python
    @pytest.mark.asyncio
    async def test_returns_sse_events(self):
        mock_connector = MagicMock()
        mock_connector.name = "kanker_nl"
        mock_connector.query = AsyncMock(
            return_value=SourceResult(
                data={"content": "Borstkanker is..."},
                summary="Informatie over borstkanker van kanker.nl",
                sources=[
                    Citation(
                        url="https://kanker.nl/borstkanker",
                        title="Borstkanker - kanker.nl",
                        reliability="official",
                    )
                ],
                visualizable=False,
            )
        )

        mock_llm_response = AsyncMock()
        mock_llm_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content="Hier zijn de bronnen over borstkanker:\n\n1. [Borstkanker - kanker.nl](https://kanker.nl/borstkanker)"
                )
            )
        ]

        connectors = {"kanker_nl": mock_connector}

        events = []
        with patch("intake.litellm.acompletion", return_value=mock_llm_response):
            async for event in search_and_format(
                ai_bekendheid="enigszins",
                gebruiker_type="patient",
                vraag_tekst="Wat is borstkanker?",
                samenvatting="U zoekt informatie over borstkanker.",
                vraag_type="patient_info",
                kankersoort="borstkanker",
                search_query="wat is borstkanker",
                connectors=connectors,
                model="test-model",
            ):
                events.append(event)

        event_types = [e.event for e in events]
        assert "source_card" in event_types
        assert "token" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_search_and_format_uses_search_query_for_vector_connectors(self):
        """kanker_nl and publications must receive search_query, not vraag_tekst."""
        mock_kanker = MagicMock()
        mock_kanker.name = "kanker_nl"
        mock_kanker.query = AsyncMock(
            return_value=SourceResult(
                data={},
                summary="",
                sources=[],
                visualizable=False,
            )
        )

        mock_publications = MagicMock()
        mock_publications.name = "publications"
        mock_publications.query = AsyncMock(
            return_value=SourceResult(
                data={},
                summary="",
                sources=[],
                visualizable=False,
            )
        )

        connectors = {"kanker_nl": mock_kanker, "publications": mock_publications}

        events = []
        async for event in search_and_format(
            ai_bekendheid="enigszins",
            gebruiker_type="onderzoeker",
            vraag_tekst="De gebruiker zoekt naar recente innovaties in kankeronderzoek",
            samenvatting="U zoekt recente innovaties.",
            vraag_type="onderzoek",
            kankersoort=None,
            search_query="welke recente innovaties zijn er in het kankeronderzoek",
            connectors=connectors,
            model="test-model",
        ):
            events.append(event)

        # Assert connectors were called with search_query, not vraag_tekst
        kanker_call_kwargs = mock_kanker.query.call_args.kwargs
        assert kanker_call_kwargs["query"] == "welke recente innovaties zijn er in het kankeronderzoek"

        pub_call_kwargs = mock_publications.query.call_args.kwargs
        assert pub_call_kwargs["query"] == "welke recente innovaties zijn er in het kankeronderzoek"
```

- [ ] **Step 2: Run the tests — expect failure**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake.py::TestSearchAndFormat -v`
Expected: FAIL — `search_and_format` doesn't accept `search_query` yet.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/backend/tests/test_intake.py
git commit -m "test: add failing tests for search_and_format search_query plumbing"
```

---

### Task 7: Implement `search_query` in `search_and_format`

**Files:**
- Modify: `teams/team5/backend/intake.py` (`search_and_format` signature and connector loop)

- [ ] **Step 1: Add `search_query` parameter and use it**

In `teams/team5/backend/intake.py`, locate `search_and_format` (currently around line 302). Replace the function signature:

```python
async def search_and_format(
    ai_bekendheid: str,
    gebruiker_type: str,
    vraag_tekst: str,
    samenvatting: str,
    vraag_type: str | None,
    kankersoort: str | None,
    connectors: dict[str, Any],
    model: str,
):
```

with:

```python
async def search_and_format(
    ai_bekendheid: str,
    gebruiker_type: str,
    vraag_tekst: str,
    samenvatting: str,
    vraag_type: str | None,
    kankersoort: str | None,
    search_query: str,
    connectors: dict[str, Any],
    model: str,
):
```

Then locate the connector query-params block (currently around line 327-338). Replace:

```python
        try:
            query_params: dict[str, Any] = {}
            if connector_name in ("kanker_nl", "publications"):
                query_params["query"] = vraag_tekst
            if kanker_filter:
                if connector_name == "kanker_nl":
                    query_params["kankersoort"] = kanker_filter
                elif connector_name in ("nkr_cijfers", "cancer_atlas"):
                    query_params["cancer_type"] = kanker_filter
            if connector_name == "nkr_cijfers":
                query_params.setdefault("cancer_type", vraag_tekst)
                query_params["period"] = "2018-2022"
```

with:

```python
        try:
            query_params: dict[str, Any] = {}
            if connector_name in ("kanker_nl", "publications"):
                query_params["query"] = search_query
            if kanker_filter:
                if connector_name == "kanker_nl":
                    query_params["kankersoort"] = kanker_filter
                elif connector_name in ("nkr_cijfers", "cancer_atlas"):
                    query_params["cancer_type"] = kanker_filter
            if connector_name == "nkr_cijfers":
                query_params.setdefault("cancer_type", vraag_tekst)
                query_params["period"] = "2018-2022"
```

- [ ] **Step 2: Run the tests — expect pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest tests/test_intake.py::TestSearchAndFormat -v`
Expected: Both tests PASS.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/backend/intake.py
git commit -m "feat(intake): search_and_format uses search_query for vector connectors"
```

---

### Task 8: Thread `search_query` through the `/api/intake/search` endpoint

**Files:**
- Modify: `teams/team5/backend/main.py` (`intake_search` endpoint)

- [ ] **Step 1: Pass `search_query` from the request into `search_and_format`**

In `teams/team5/backend/main.py`, locate the `intake_search` endpoint (currently around line 513-541). Replace:

```python
            async for sse_event in search_and_format(
                ai_bekendheid=request.ai_bekendheid,
                gebruiker_type=request.gebruiker_type,
                vraag_tekst=request.vraag_tekst,
                samenvatting=request.samenvatting,
                vraag_type=request.vraag_type,
                kankersoort=request.kankersoort,
                connectors=connector_dict,
                model=LLM_MODEL,
            ):
```

with:

```python
            async for sse_event in search_and_format(
                ai_bekendheid=request.ai_bekendheid,
                gebruiker_type=request.gebruiker_type,
                vraag_tekst=request.vraag_tekst,
                samenvatting=request.samenvatting,
                vraag_type=request.vraag_type,
                kankersoort=request.kankersoort,
                search_query=request.search_query,
                connectors=connector_dict,
                model=LLM_MODEL,
            ):
```

- [ ] **Step 2: Run the full backend test suite**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add teams/team5/backend/main.py
git commit -m "api: thread search_query through /api/intake/search"
```

---

### Task 9: Add `search_query` to frontend types

**Files:**
- Modify: `teams/team5/frontend/lib/types.ts`

- [ ] **Step 1: Update `GegevensModel` interface**

In `teams/team5/frontend/lib/types.ts`, replace:

```typescript
export interface GegevensModel {
  ai_bekendheid: AiBekendheid | null;
  gebruiker_type: GebruikerType | null;
  vraag_tekst: string | null;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string | null;
  bevestigd: boolean;
}
```

with:

```typescript
export interface GegevensModel {
  ai_bekendheid: AiBekendheid | null;
  gebruiker_type: GebruikerType | null;
  vraag_tekst: string | null;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string | null;
  search_query: string | null;
  bevestigd: boolean;
}
```

- [ ] **Step 2: Update `IntakeSummarizeResponse` interface**

Replace:

```typescript
export interface IntakeSummarizeResponse {
  samenvatting: string;
  kankersoort: string;
  vraag_type: string;
}
```

with:

```typescript
export interface IntakeSummarizeResponse {
  samenvatting: string;
  kankersoort: string;
  vraag_type: string;
  search_query: string;
}
```

- [ ] **Step 3: Commit**

```bash
git add teams/team5/frontend/lib/types.ts
git commit -m "frontend: add search_query to intake types"
```

---

### Task 10: Send `search_query` from the frontend `searchAndStream` client

**Files:**
- Modify: `teams/team5/frontend/lib/intake-client.ts` (`searchAndStream` signature)

- [ ] **Step 1: Add `search_query` to the request type**

In `teams/team5/frontend/lib/intake-client.ts`, replace:

```typescript
export async function* searchAndStream(request: {
  ai_bekendheid: string;
  gebruiker_type: string;
  vraag_tekst: string;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string;
}): AsyncGenerator<SSEEvent> {
```

with:

```typescript
export async function* searchAndStream(request: {
  ai_bekendheid: string;
  gebruiker_type: string;
  vraag_tekst: string;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string;
  search_query: string;
}): AsyncGenerator<SSEEvent> {
```

- [ ] **Step 2: Commit**

```bash
git add teams/team5/frontend/lib/intake-client.ts
git commit -m "frontend: add search_query to searchAndStream client"
```

---

### Task 11: Update the chat page state to carry and pass `search_query`

**Files:**
- Modify: `teams/team5/frontend/app/page.tsx`

- [ ] **Step 1: Add `search_query` to `INITIAL_GEGEVENS`**

In `teams/team5/frontend/app/page.tsx`, replace:

```typescript
const INITIAL_GEGEVENS: GegevensModel = {
  ai_bekendheid: null,
  gebruiker_type: null,
  vraag_tekst: null,
  kankersoort: null,
  vraag_type: null,
  samenvatting: null,
  bevestigd: false,
};
```

with:

```typescript
const INITIAL_GEGEVENS: GegevensModel = {
  ai_bekendheid: null,
  gebruiker_type: null,
  vraag_tekst: null,
  kankersoort: null,
  vraag_type: null,
  samenvatting: null,
  search_query: null,
  bevestigd: false,
};
```

- [ ] **Step 2: Add `search_query` to the other `samenvatting: null` reset sites**

There are two other locations in `page.tsx` (around lines 169 and 254) that reset gegevens fields including `samenvatting: null`. For each of those two reset blocks, find the `samenvatting: null,` line and add `search_query: null,` on the line immediately after it.

For example, replace:

```typescript
        samenvatting: null,
```

with:

```typescript
        samenvatting: null,
        search_query: null,
```

Apply this at both line 169 and line 254 reset sites (and any other spot where gegevens is partially reset with `samenvatting: null`).

- [ ] **Step 3: Also reset `search_query` where vraag_tekst/samenvatting are cleared**

Locate the line (around line 418) that currently reads:

```typescript
                    setGegevens((prev) => ({ ...prev, vraag_tekst: null, samenvatting: null, vraag_type: null }));
```

Replace it with:

```typescript
                    setGegevens((prev) => ({ ...prev, vraag_tekst: null, samenvatting: null, vraag_type: null, search_query: null }));
```

- [ ] **Step 4: Pass `search_query` to `searchAndStream`**

Locate the `searchAndStream` call (currently around line 189). Replace:

```typescript
      const stream = searchAndStream({
        ai_bekendheid: g.ai_bekendheid || "enigszins",
        gebruiker_type: g.gebruiker_type || "publiek",
        vraag_tekst: g.vraag_tekst || "",
        kankersoort: g.kankersoort,
        vraag_type: g.vraag_type,
        samenvatting: g.samenvatting || g.vraag_tekst || "",
      });
```

with:

```typescript
      const stream = searchAndStream({
        ai_bekendheid: g.ai_bekendheid || "enigszins",
        gebruiker_type: g.gebruiker_type || "publiek",
        vraag_tekst: g.vraag_tekst || "",
        kankersoort: g.kankersoort,
        vraag_type: g.vraag_type,
        samenvatting: g.samenvatting || g.vraag_tekst || "",
        search_query: g.search_query || g.vraag_tekst || "",
      });
```

- [ ] **Step 5: Type-check the frontend**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add teams/team5/frontend/app/page.tsx
git commit -m "frontend: carry search_query in chat page state and send to search"
```

---

### Task 12: End-to-end smoke check

**Files:** None (verification only)

- [ ] **Step 1: Run the full backend test suite one last time**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run python -m pytest -v`
Expected: All tests PASS.

- [ ] **Step 2: Confirm no `vraag_tekst` is passed as the vector query anywhere**

Run:

```bash
cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && grep -n 'query_params\["query"\] = vraag_tekst' intake.py
```

Expected: no matches (the replacement in Task 7 removed this line).

- [ ] **Step 3: Confirm `search_query` is referenced in all the right places**

Run:

```bash
cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5 && grep -rn search_query backend/intake_graph.py backend/intake.py backend/main.py backend/models.py frontend/lib/types.ts frontend/lib/intake-client.ts frontend/app/page.tsx
```

Expected: at least one hit in each file.
