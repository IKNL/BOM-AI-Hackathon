# Intake Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the free-form chat with a structured intake -> validate -> search flow that guides users through button-based questions, confirms understanding via LLM summary, then returns targeted source links.

**Architecture:** Frontend state machine (INTAKE_START -> GEBRUIKER_TYPE -> VRAAG -> SAMENVATTING -> RESULTS) drives deterministic intake steps. Backend exposes two new endpoints: `/api/intake/summarize` (single LLM call) and `/api/intake/search` (connector queries + LLM formatting). The existing orchestrator stays intact as fallback; new `intake.py` module handles the new flow.

**Tech Stack:** FastAPI + Pydantic (backend), Next.js 14 + TypeScript + Tailwind (frontend), LiteLLM for LLM calls, existing ChromaDB connectors.

---

### Task 1: Add GegevensModel + intake request/response models

**Files:**
- Modify: `backend/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing tests for GegevensModel**

```python
# Add to backend/tests/test_models.py

from models import GegevensModel, IntakeSummarizeRequest, IntakeSummarizeResponse, IntakeSearchRequest


class TestGegevensModel:
    def test_defaults(self):
        gm = GegevensModel()
        assert gm.ai_bekendheid is None
        assert gm.gebruiker_type is None
        assert gm.vraag_tekst is None
        assert gm.kankersoort is None
        assert gm.vraag_type is None
        assert gm.samenvatting is None
        assert gm.bevestigd is False

    def test_valid_ai_bekendheid(self):
        gm = GegevensModel(ai_bekendheid="niet_bekend")
        assert gm.ai_bekendheid == "niet_bekend"

    def test_invalid_ai_bekendheid_rejected(self):
        with pytest.raises(ValidationError):
            GegevensModel(ai_bekendheid="very_known")

    def test_valid_gebruiker_type(self):
        gm = GegevensModel(gebruiker_type="patient")
        assert gm.gebruiker_type == "patient"

    def test_invalid_gebruiker_type_rejected(self):
        with pytest.raises(ValidationError):
            GegevensModel(gebruiker_type="hacker")

    def test_full_model(self):
        gm = GegevensModel(
            ai_bekendheid="enigszins",
            gebruiker_type="zorgverlener",
            vraag_tekst="Hoe vaak komt longkanker voor?",
            kankersoort="longkanker",
            vraag_type="cijfers",
            samenvatting="U zoekt cijfers over longkanker.",
            bevestigd=True,
        )
        assert gm.bevestigd is True
        assert gm.kankersoort == "longkanker"


class TestIntakeSummarizeRequest:
    def test_valid(self):
        req = IntakeSummarizeRequest(
            gebruiker_type="patient",
            vraag_tekst="Wat is borstkanker?",
        )
        assert req.gebruiker_type == "patient"
        assert req.vraag_tekst == "Wat is borstkanker?"

    def test_invalid_gebruiker_type(self):
        with pytest.raises(ValidationError):
            IntakeSummarizeRequest(
                gebruiker_type="alien",
                vraag_tekst="test",
            )


class TestIntakeSummarizeResponse:
    def test_valid(self):
        resp = IntakeSummarizeResponse(
            samenvatting="U zoekt info over borstkanker.",
            kankersoort="borstkanker",
            vraag_type="patient_info",
        )
        assert resp.kankersoort == "borstkanker"

    def test_geen_kankersoort(self):
        resp = IntakeSummarizeResponse(
            samenvatting="U zoekt algemene info.",
            kankersoort="geen",
            vraag_type="breed",
        )
        assert resp.kankersoort == "geen"


class TestIntakeSearchRequest:
    def test_valid(self):
        req = IntakeSearchRequest(
            ai_bekendheid="erg_bekend",
            gebruiker_type="onderzoeker",
            vraag_tekst="Overleving darmkanker",
            kankersoort="darmkanker",
            vraag_type="cijfers",
            samenvatting="U zoekt overlevingscijfers voor darmkanker.",
        )
        assert req.gebruiker_type == "onderzoeker"

    def test_requires_gebruiker_type(self):
        with pytest.raises(ValidationError):
            IntakeSearchRequest(
                ai_bekendheid="enigszins",
                vraag_tekst="test",
                samenvatting="test",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'GegevensModel'`

- [ ] **Step 3: Implement the models**

Add to `backend/models.py` after the existing `SessionContext` class:

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


class IntakeSummarizeRequest(BaseModel):
    """Request body for /api/intake/summarize."""
    gebruiker_type: Literal[
        "patient", "publiek", "zorgverlener", "student",
        "beleidsmaker", "onderzoeker", "journalist", "anders"
    ]
    vraag_tekst: str


class IntakeSummarizeResponse(BaseModel):
    """Response from /api/intake/summarize."""
    samenvatting: str
    kankersoort: str  # "geen" if not mentioned
    vraag_type: str   # patient_info | cijfers | regionaal | onderzoek | breed


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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add GegevensModel + intake request/response models"
```

---

### Task 2: Implement intake summarize logic

**Files:**
- Create: `backend/intake.py`
- Test: `backend/tests/test_intake.py`

- [ ] **Step 1: Write failing test for summarize**

Create `backend/tests/test_intake.py`:

```python
"""Tests for intake module — summarize and search logic."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from intake import summarize_question
from models import IntakeSummarizeResponse


class TestSummarizeQuestion:
    @pytest.mark.asyncio
    async def test_returns_summarize_response(self):
        """summarize_question should return an IntakeSummarizeResponse."""
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

    @pytest.mark.asyncio
    async def test_handles_geen_kankersoort(self):
        """When no cancer type is mentioned, kankersoort should be 'geen'."""
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content=json.dumps({
                        "samenvatting": "U zoekt algemene informatie over kanker.",
                        "kankersoort": "geen",
                        "vraag_type": "breed",
                    })
                )
            )
        ]

        with patch("intake.litellm.acompletion", return_value=mock_response):
            result = await summarize_question(
                gebruiker_type="publiek",
                vraag_tekst="Wat doet IKNL?",
                model="test-model",
            )

        assert result.kankersoort == "geen"
        assert result.vraag_type == "breed"

    @pytest.mark.asyncio
    async def test_llm_returns_non_json_falls_back(self):
        """If LLM returns non-JSON, summarize should return a fallback."""
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(content="This is not JSON")
            )
        ]

        with patch("intake.litellm.acompletion", return_value=mock_response):
            result = await summarize_question(
                gebruiker_type="patient",
                vraag_tekst="Wat is borstkanker?",
                model="test-model",
            )

        # Should still return a valid response with fallback values
        assert isinstance(result, IntakeSummarizeResponse)
        assert result.vraag_type == "breed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'intake'`

- [ ] **Step 3: Implement summarize_question**

Create `backend/intake.py`:

```python
"""
Intake module: structured summarize + search flow.

Replaces the free-form tool-use orchestrator with two focused operations:
1. summarize_question — single LLM call to summarize user intent
2. search_and_format — query connectors + LLM formatting of results
"""

import json
import logging
from typing import Any

import litellm

from models import IntakeSummarizeResponse, SourceResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summarize prompt (from spec)
# ---------------------------------------------------------------------------

_SUMMARIZE_PROMPT_TEMPLATE = """Je bent een intake-assistent. De gebruiker heeft de volgende informatie gegeven:
- Type gebruiker: {gebruiker_type}
- Vraag: {vraag_tekst}

Doe drie dingen:
1. Schrijf een korte, natuurlijke samenvatting van wat de gebruiker zoekt (max 2 zinnen).
2. Als de gebruiker een specifiek type kanker noemt, geef die naam terug als "kankersoort". Zo niet, antwoord "geen". Vraag NOOIT zelf naar een kankersoort.
3. Classificeer welk type informatie de gebruiker zoekt als "vraag_type". Kies uit:
   - "patient_info" — algemene informatie, symptomen, behandeling, leven met kanker
   - "cijfers" — statistieken, incidentie, overleving, prevalentie
   - "regionaal" — regionale verschillen, gebiedsvergelijking
   - "onderzoek" — wetenschappelijke publicaties, rapporten, studies
   - "breed" — combinatie of onduidelijk

Antwoord in JSON:
{{"samenvatting": "...", "kankersoort": "..." of "geen", "vraag_type": "..."}}"""


async def summarize_question(
    gebruiker_type: str,
    vraag_tekst: str,
    model: str,
) -> IntakeSummarizeResponse:
    """Call LLM to summarize the user's question, extract kankersoort, classify vraag_type."""
    prompt = _SUMMARIZE_PROMPT_TEMPLATE.format(
        gebruiker_type=gebruiker_type,
        vraag_tekst=vraag_tekst,
    )

    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content or ""

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/intake.py backend/tests/test_intake.py
git commit -m "feat: add intake summarize logic with LLM call"
```

---

### Task 3: Implement intake search logic

**Files:**
- Modify: `backend/intake.py`
- Modify: `backend/tests/test_intake.py`

- [ ] **Step 1: Write failing tests for search_and_format**

Append to `backend/tests/test_intake.py`:

```python
from unittest.mock import MagicMock
from intake import search_and_format, _select_connectors
from models import Citation


class TestSelectConnectors:
    def test_patient_with_patient_info(self):
        """Patient asking patient_info question → kanker_nl first."""
        result = _select_connectors("patient", "patient_info")
        assert result[0] == "kanker_nl"

    def test_onderzoeker_with_onderzoek(self):
        """Researcher asking research question → publications first."""
        result = _select_connectors("onderzoeker", "onderzoek")
        assert result[0] == "publications"

    def test_beleidsmaker_with_regionaal(self):
        """Policymaker asking regional question → cancer_atlas first."""
        result = _select_connectors("beleidsmaker", "regionaal")
        assert result[0] == "cancer_atlas"

    def test_patient_with_cijfers(self):
        """Patient asking about statistics → nkr_cijfers included."""
        result = _select_connectors("patient", "cijfers")
        assert "nkr_cijfers" in result


class TestSearchAndFormat:
    @pytest.mark.asyncio
    async def test_returns_sse_events(self):
        """search_and_format should yield SSE events."""
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
                connectors=connectors,
                model="test-model",
            ):
                events.append(event)

        event_types = [e.event for e in events]
        assert "source_card" in event_types
        assert "token" in event_types
        assert "done" in event_types
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py::TestSelectConnectors -v`
Expected: FAIL — `ImportError: cannot import name '_select_connectors'`

- [ ] **Step 3: Implement _select_connectors and search_and_format**

Append to `backend/intake.py`:

```python
from dataclasses import dataclass

@dataclass
class SSEEvent:
    """A single Server-Sent Event."""
    event: str
    data: str


# ---------------------------------------------------------------------------
# Source priority tables (from spec)
# ---------------------------------------------------------------------------

# Maps (gebruiker_type) → ordered list of connector names
_TYPE_PRIORITY: dict[str, list[str]] = {
    "patient":      ["kanker_nl", "nkr_cijfers", "publications", "cancer_atlas"],
    "publiek":      ["kanker_nl", "nkr_cijfers", "publications", "cancer_atlas"],
    "zorgverlener": ["nkr_cijfers", "publications", "kanker_nl", "cancer_atlas"],
    "student":      ["publications", "nkr_cijfers", "kanker_nl", "cancer_atlas"],
    "onderzoeker":  ["publications", "nkr_cijfers", "kanker_nl", "cancer_atlas"],
    "beleidsmaker": ["cancer_atlas", "nkr_cijfers", "publications", "kanker_nl"],
    "journalist":   ["kanker_nl", "nkr_cijfers", "cancer_atlas", "publications"],
    "anders":       ["kanker_nl", "nkr_cijfers", "cancer_atlas", "publications"],
}

# Maps vraag_type → which connectors are relevant
_VRAAG_TYPE_CONNECTORS: dict[str, set[str]] = {
    "patient_info": {"kanker_nl", "publications"},
    "cijfers":      {"nkr_cijfers", "kanker_nl"},
    "regionaal":    {"cancer_atlas", "nkr_cijfers"},
    "onderzoek":    {"publications", "nkr_cijfers"},
    "breed":        {"kanker_nl", "nkr_cijfers", "cancer_atlas", "publications"},
}


def _select_connectors(gebruiker_type: str, vraag_type: str | None) -> list[str]:
    """Select and order connectors based on user type and question type.

    1. Match by vraag_type first (which sources are relevant to the question).
    2. Order by gebruiker_type priority (tiebreaker).
    """
    relevant = _VRAAG_TYPE_CONNECTORS.get(vraag_type or "breed", _VRAAG_TYPE_CONNECTORS["breed"])
    priority = _TYPE_PRIORITY.get(gebruiker_type, _TYPE_PRIORITY["anders"])

    # Return priority-ordered list filtered to relevant connectors
    ordered = [c for c in priority if c in relevant]
    # Add any relevant connectors not in the priority list
    for c in relevant:
        if c not in ordered:
            ordered.append(c)
    return ordered


# ---------------------------------------------------------------------------
# Response formatting prompt (from spec)
# ---------------------------------------------------------------------------

_FORMAT_PROMPT_TEMPLATE = """Je bent een informatieassistent. De gebruiker is een {gebruiker_type} en zoekt: {samenvatting}.

Hieronder staan de gevonden bronnen. Maak een antwoord in dit formaat:
1. Herhaal kort de vraag van de gebruiker
2. Noem maximaal 5 bronnen met voor elke bron:
   - De naam en URL
   - Eén zin over wat daar te vinden is met betrekking tot de vraag
3. Sluit af met: "Zoekt u meer informatie of heeft u een nieuwe vraag?"

BELANGRIJK: Vat geen medische inhoud samen. Verwijs alleen naar de bron.
Pas je taalgebruik aan op basis van de bekendheid: {ai_bekendheid}

Gevonden bronnen:
{bronnen_tekst}"""

_GUIDANCE_LEVEL = {
    "niet_bekend": "Eenvoudig taalgebruik, uitleg wat elke bron is, stap-voor-stap",
    "enigszins": "Standaard, beknopte bronbeschrijvingen",
    "erg_bekend": "Compact, geen uitleg, snelle weergave",
}


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
    """Query connectors and format results via LLM. Yields SSEEvent objects."""
    import uuid

    message_id = str(uuid.uuid4())
    sources_tried: list[str] = []
    all_sources: list[dict] = []

    # Select which connectors to query and in what order
    connector_order = _select_connectors(gebruiker_type, vraag_type)

    # Normalize kankersoort
    kanker_filter = kankersoort if kankersoort and kankersoort != "geen" else None

    # Query connectors
    for connector_name in connector_order:
        if connector_name not in connectors:
            continue

        connector = connectors[connector_name]
        sources_tried.append(connector_name)

        try:
            # Build query params based on connector type
            query_params: dict[str, Any] = {"query": vraag_tekst}
            if kanker_filter:
                if connector_name == "kanker_nl":
                    query_params["kankersoort"] = kanker_filter
                elif connector_name in ("nkr_cijfers", "cancer_atlas"):
                    query_params["cancer_type"] = kanker_filter

            result = await connector.query(**query_params)

            contributed = result.data is not None and result.data != {}

            # Emit source cards
            if result.sources:
                for source in result.sources:
                    card = {
                        "source": connector_name,
                        "url": source.url,
                        "reliability": source.reliability,
                        "contributed": contributed,
                    }
                    yield SSEEvent(
                        event="source_card",
                        data=json.dumps(card, ensure_ascii=False),
                    )
                    if contributed:
                        all_sources.append({
                            "title": source.title,
                            "url": source.url,
                            "summary": result.summary,
                            "source": connector_name,
                        })
            else:
                yield SSEEvent(
                    event="source_card",
                    data=json.dumps({
                        "source": connector_name,
                        "url": "",
                        "reliability": "",
                        "contributed": False,
                    }, ensure_ascii=False),
                )

            # Stop if we have 5+ results
            if len(all_sources) >= 5:
                break

        except Exception as exc:
            logger.warning("Connector %s failed: %s", connector_name, exc)
            yield SSEEvent(
                event="source_card",
                data=json.dumps({
                    "source": connector_name,
                    "url": "",
                    "reliability": "",
                    "contributed": False,
                }, ensure_ascii=False),
            )

    # Format results via LLM
    if all_sources:
        bronnen_tekst = "\n".join(
            f"- [{s['title']}]({s['url']}) ({s['source']}): {s['summary']}"
            for s in all_sources[:5]
        )
    else:
        bronnen_tekst = "Geen relevante bronnen gevonden."

    guidance = _GUIDANCE_LEVEL.get(ai_bekendheid, _GUIDANCE_LEVEL["enigszins"])
    format_prompt = _FORMAT_PROMPT_TEMPLATE.format(
        gebruiker_type=gebruiker_type,
        samenvatting=samenvatting,
        ai_bekendheid=guidance,
        bronnen_tekst=bronnen_tekst,
    )

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": format_prompt}],
            temperature=0.3,
        )
        final_text = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("LLM formatting failed")
        final_text = (
            "Er is een fout opgetreden bij het formatteren van de resultaten. "
            "De gevonden bronnen staan hieronder.\n\n" + bronnen_tekst
        )

    # Stream tokens
    chunk_size = 20
    for i in range(0, len(final_text), chunk_size):
        chunk = final_text[i : i + chunk_size]
        yield SSEEvent(
            event="token",
            data=json.dumps({"text": chunk}, ensure_ascii=False),
        )

    yield SSEEvent(
        event="done",
        data=json.dumps({
            "message_id": message_id,
            "sources_tried": sources_tried,
        }, ensure_ascii=False),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/intake.py backend/tests/test_intake.py
git commit -m "feat: add intake search logic with connector selection + LLM formatting"
```

---

### Task 4: Add backend intake endpoints

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing test for endpoints**

Append to `backend/tests/test_intake.py`:

```python
from httpx import ASGITransport, AsyncClient


class TestIntakeEndpoints:
    @pytest.mark.asyncio
    async def test_summarize_endpoint(self):
        """POST /api/intake/summarize should return summarize response."""
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
            from main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/intake/summarize", json={
                    "gebruiker_type": "patient",
                    "vraag_tekst": "Wat is borstkanker?",
                })

        assert resp.status_code == 200
        data = resp.json()
        assert "samenvatting" in data
        assert "kankersoort" in data
        assert "vraag_type" in data

    @pytest.mark.asyncio
    async def test_summarize_invalid_type(self):
        """POST /api/intake/summarize with invalid type should 422."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/intake/summarize", json={
                "gebruiker_type": "alien",
                "vraag_tekst": "test",
            })

        assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py::TestIntakeEndpoints -v`
Expected: FAIL — 404 (endpoint doesn't exist yet)

- [ ] **Step 3: Add endpoints to main.py**

Add to `backend/main.py` after the existing imports:

```python
from models import IntakeSummarizeRequest, IntakeSearchRequest
from intake import summarize_question, search_and_format
```

Add endpoints after the existing `/api/chat/stream` endpoint:

```python
@app.post("/api/intake/summarize")
async def intake_summarize(request: IntakeSummarizeRequest):
    """Summarize user question, extract kankersoort, classify vraag_type."""
    result = await summarize_question(
        gebruiker_type=request.gebruiker_type,
        vraag_tekst=request.vraag_tekst,
        model=LLM_MODEL,
    )
    return result.model_dump()


@app.post("/api/intake/search")
async def intake_search(request: IntakeSearchRequest):
    """Query connectors and stream formatted results."""
    connector_dict = {c.name: c for c in _connectors}

    async def event_generator():
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
            yield {
                "event": sse_event.event,
                "data": sse_event.data,
            }

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/test_intake.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_intake.py
git commit -m "feat: add /api/intake/summarize and /api/intake/search endpoints"
```

---

### Task 5: Add frontend types + intake API client

**Files:**
- Modify: `frontend/lib/types.ts`
- Create: `frontend/lib/intake-client.ts`

- [ ] **Step 1: Add intake types to types.ts**

Add to end of `frontend/lib/types.ts`:

```typescript
// Intake flow types

export type AiBekendheid = "niet_bekend" | "enigszins" | "erg_bekend";

export type GebruikerType =
  | "patient"
  | "publiek"
  | "zorgverlener"
  | "student"
  | "beleidsmaker"
  | "onderzoeker"
  | "journalist"
  | "anders";

export type IntakeState =
  | "INTAKE_START"
  | "GEBRUIKER_TYPE"
  | "VRAAG"
  | "SAMENVATTING"
  | "SEARCH"
  | "RESULTS";

export interface GegevensModel {
  ai_bekendheid: AiBekendheid | null;
  gebruiker_type: GebruikerType | null;
  vraag_tekst: string | null;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string | null;
  bevestigd: boolean;
}

export interface IntakeSummarizeResponse {
  samenvatting: string;
  kankersoort: string;
  vraag_type: string;
}
```

- [ ] **Step 2: Create intake-client.ts**

Create `frontend/lib/intake-client.ts`:

```typescript
import type { IntakeSummarizeResponse, SSEEvent } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function parseSSELine(line: string): { event?: string; data?: string } | null {
  if (line.startsWith("event:")) return { event: line.slice(6).trim() };
  if (line.startsWith("data:")) return { data: line.slice(5).trim() };
  return null;
}

export async function summarizeQuestion(
  gebruiker_type: string,
  vraag_tekst: string
): Promise<IntakeSummarizeResponse> {
  const response = await fetch(`${API_BASE}/api/intake/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gebruiker_type, vraag_tekst }),
  });
  if (!response.ok) {
    throw new Error(`Summarize failed: ${response.status}`);
  }
  return response.json();
}

export async function* searchAndStream(request: {
  ai_bekendheid: string;
  gebruiker_type: string;
  vraag_tekst: string;
  kankersoort: string | null;
  vraag_type: string | null;
  samenvatting: string;
}): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/api/intake/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    yield {
      event: "error",
      data: {
        code: `HTTP_${response.status}`,
        message: `Server returned ${response.status}: ${response.statusText}`,
      },
    };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { event: "error", data: { code: "NO_BODY", message: "Empty response" } };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "token";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed === "") continue;

        const parsed = parseSSELine(trimmed);
        if (!parsed) continue;

        if (parsed.event !== undefined) currentEvent = parsed.event;

        if (parsed.data !== undefined) {
          try {
            const jsonData = JSON.parse(parsed.data);
            yield { event: currentEvent as SSEEvent["event"], data: jsonData };
            if (currentEvent === "done" || currentEvent === "error") return;
          } catch {
            if (currentEvent === "token") {
              yield { event: "token", data: { text: parsed.data } };
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/intake-client.ts
git commit -m "feat: add frontend intake types and API client"
```

---

### Task 6: Create IntakeButtons component

**Files:**
- Create: `frontend/components/IntakeButtons.tsx`

- [ ] **Step 1: Create IntakeButtons component**

Create `frontend/components/IntakeButtons.tsx`:

```tsx
"use client";

import React from "react";

interface ButtonOption {
  value: string;
  label: string;
}

interface IntakeButtonsProps {
  options: ButtonOption[];
  onSelect: (value: string) => void;
  columns?: 1 | 2;
}

export default function IntakeButtons({
  options,
  onSelect,
  columns = 1,
}: IntakeButtonsProps) {
  return (
    <div
      className={`grid gap-2 ${
        columns === 2 ? "grid-cols-2" : "grid-cols-1"
      } max-w-md`}
    >
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onSelect(option.value)}
          className="px-4 py-3 text-left text-sm font-medium rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-teal-50 hover:border-teal-300 hover:text-teal-800 transition-colors"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/IntakeButtons.tsx
git commit -m "feat: add IntakeButtons component"
```

---

### Task 7: Create ResultsList component

**Files:**
- Create: `frontend/components/ResultsList.tsx`

- [ ] **Step 1: Create ResultsList component**

Create `frontend/components/ResultsList.tsx`:

```tsx
"use client";

import React from "react";

interface ResultsListProps {
  content: string;
  onMoreInfo: () => void;
  onNewTopic: () => void;
}

export default function ResultsList({
  content,
  onMoreInfo,
  onNewTopic,
}: ResultsListProps) {
  // Simple markdown-like rendering: links + bold + line breaks
  const renderContent = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, i) => {
      // Convert markdown links [text](url) to actual links
      const withLinks = line.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-teal-700 underline hover:text-teal-900">$1</a>'
      );
      // Convert **bold**
      const withBold = withLinks.replace(
        /\*\*([^*]+)\*\*/g,
        "<strong>$1</strong>"
      );
      return (
        <p
          key={i}
          className={`${line.trim() === "" ? "h-3" : ""}`}
          dangerouslySetInnerHTML={{ __html: withBold }}
        />
      );
    });
  };

  return (
    <div>
      <div className="prose prose-sm max-w-none text-gray-800 space-y-1">
        {renderContent(content)}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={onMoreInfo}
          className="px-4 py-2.5 text-sm font-medium rounded-xl border border-teal-300 bg-teal-50 text-teal-800 hover:bg-teal-100 transition-colors"
        >
          Meer informatie
        </button>
        <button
          onClick={onNewTopic}
          className="px-4 py-2.5 text-sm font-medium rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Nieuw onderwerp
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ResultsList.tsx
git commit -m "feat: add ResultsList component with follow-up buttons"
```

---

### Task 8: Rewrite frontend page.tsx as intake state machine

**Files:**
- Modify: `frontend/app/page.tsx`

This is the largest task. The page.tsx gets rewritten from a free-form chat to a state-machine-driven intake flow.

- [ ] **Step 1: Rewrite page.tsx**

Replace the entire content of `frontend/app/page.tsx` with:

```tsx
"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import type {
  ChatMessage as ChatMessageType,
  SourceCard,
  IntakeState,
  AiBekendheid,
  GebruikerType,
  GegevensModel,
} from "@/lib/types";
import { summarizeQuestion, searchAndStream } from "@/lib/intake-client";
import ChatMessage from "@/components/ChatMessage";
import IntakeButtons from "@/components/IntakeButtons";
import ResultsList from "@/components/ResultsList";

function generateId(): string {
  return crypto.randomUUID();
}

const BEKENDHEID_OPTIONS = [
  { value: "niet_bekend", label: "Niet bekend" },
  { value: "enigszins", label: "Enigszins bekend" },
  { value: "erg_bekend", label: "Erg bekend" },
];

const GEBRUIKER_OPTIONS = [
  { value: "patient", label: "Ik ben patiënt of naaste" },
  { value: "publiek", label: "Ik ben algemeen publiek" },
  { value: "zorgverlener", label: "Ik ben een zorgverlener" },
  { value: "student", label: "Ik ben een student of docent" },
  { value: "beleidsmaker", label: "Ik ben een beleidsmaker" },
  { value: "onderzoeker", label: "Ik ben een onderzoeker of wetenschapper" },
  { value: "journalist", label: "Ik ben een journalist" },
  { value: "anders", label: "Anders" },
];

const GEBRUIKER_LABELS: Record<string, string> = {
  patient: "patiënt of naaste",
  publiek: "algemeen publiek",
  zorgverlener: "zorgverlener",
  student: "student of docent",
  beleidsmaker: "beleidsmaker",
  onderzoeker: "onderzoeker of wetenschapper",
  journalist: "journalist",
  anders: "anders",
};

const INITIAL_GEGEVENS: GegevensModel = {
  ai_bekendheid: null,
  gebruiker_type: null,
  vraag_tekst: null,
  kankersoort: null,
  vraag_type: null,
  samenvatting: null,
  bevestigd: false,
};

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [intakeState, setIntakeState] = useState<IntakeState>("INTAKE_START");
  const [gegevens, setGegevens] = useState<GegevensModel>(INITIAL_GEGEVENS);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [resultContent, setResultContent] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState("pending");

  useEffect(() => {
    setCurrentSessionId(generateId());
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, intakeState, resultContent, scrollToBottom]);

  // Add a bot message to the conversation
  const addBotMessage = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content, id: generateId() },
    ]);
  }, []);

  // Add a user message to the conversation
  const addUserMessage = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", content, id: generateId() },
    ]);
  }, []);

  // Show initial welcome + first question on mount
  useEffect(() => {
    addBotMessage(
      "Welkom bij de IKNL Infobot! Ik help u betrouwbare kankerinformatie te vinden.\n\n" +
        "**Let op:** Dit is een prototype (BrabantHack_26). Dit is geen medisch hulpmiddel.\n\n" +
        "Laten we beginnen. **Hoe bekend bent u met het gebruiken van een AI-chatbot?**"
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- State machine handlers ---

  const handleBekendheid = (value: string) => {
    addUserMessage(
      BEKENDHEID_OPTIONS.find((o) => o.value === value)?.label || value
    );
    setGegevens((prev) => ({
      ...prev,
      ai_bekendheid: value as AiBekendheid,
    }));
    addBotMessage("**Waaronder valt u?**");
    setIntakeState("GEBRUIKER_TYPE");
  };

  const handleGebruikerType = (value: string) => {
    addUserMessage(
      GEBRUIKER_OPTIONS.find((o) => o.value === value)?.label || value
    );
    setGegevens((prev) => ({
      ...prev,
      gebruiker_type: value as GebruikerType,
    }));

    const prompt =
      gegevens.ai_bekendheid === "niet_bekend"
        ? "**Schrijf in één zin duidelijk uw vraag op.**"
        : "**Wat is uw vraag?**";
    addBotMessage(prompt);
    setIntakeState("VRAAG");
  };

  const handleVraagSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;

    addUserMessage(text);
    setInputText("");
    setGegevens((prev) => ({ ...prev, vraag_tekst: text }));
    setIsLoading(true);

    try {
      const result = await summarizeQuestion(
        gegevens.gebruiker_type!,
        text
      );
      setGegevens((prev) => ({
        ...prev,
        samenvatting: result.samenvatting,
        kankersoort: result.kankersoort === "geen" ? null : result.kankersoort,
        vraag_type: result.vraag_type,
      }));

      const typeLabel = GEBRUIKER_LABELS[gegevens.gebruiker_type!] || gegevens.gebruiker_type;
      addBotMessage(
        `Als ik het goed begrijp is dit uw vraag:\n\n` +
          `> U bent een **${typeLabel}** en zoekt informatie over: *${result.samenvatting}*\n\n` +
          `**Klopt dit?**`
      );
      setIntakeState("SAMENVATTING");
    } catch (err) {
      addBotMessage(
        "Er is een fout opgetreden bij het verwerken van uw vraag. Probeer het opnieuw."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async (confirmed: boolean) => {
    if (confirmed) {
      addUserMessage("Ja, dit klopt");
      setGegevens((prev) => ({ ...prev, bevestigd: true }));
      setIntakeState("SEARCH");
      setIsLoading(true);
      setResultContent("");

      // Create a placeholder assistant message for streaming
      const resultMsgId = generateId();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", id: resultMsgId, sourceCards: [] },
      ]);

      try {
        const stream = searchAndStream({
          ai_bekendheid: gegevens.ai_bekendheid!,
          gebruiker_type: gegevens.gebruiker_type!,
          vraag_tekst: gegevens.vraag_tekst!,
          kankersoort: gegevens.kankersoort,
          vraag_type: gegevens.vraag_type,
          samenvatting: gegevens.samenvatting!,
        });

        let fullText = "";

        for await (const event of stream) {
          switch (event.event) {
            case "token": {
              const tokenText = (event.data as { text: string }).text;
              fullText += tokenText;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === resultMsgId
                    ? { ...m, content: m.content + tokenText }
                    : m
                )
              );
              break;
            }
            case "source_card": {
              const card = event.data as unknown as SourceCard;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === resultMsgId
                    ? { ...m, sourceCards: [...(m.sourceCards || []), card] }
                    : m
                )
              );
              break;
            }
            case "done":
              break;
            case "error": {
              const errMsg = (event.data as { message: string }).message;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === resultMsgId
                    ? { ...m, content: m.content + `\n\nFout: ${errMsg}` }
                    : m
                )
              );
              break;
            }
          }
        }

        setResultContent(fullText);
        setIntakeState("RESULTS");
      } catch {
        addBotMessage("Er is een verbindingsfout opgetreden. Probeer het opnieuw.");
        setIntakeState("SAMENVATTING");
      } finally {
        setIsLoading(false);
      }
    } else {
      addUserMessage("Nee, ik wil iets aanpassen");
      addBotMessage("Geen probleem. **Waaronder valt u?**");
      setGegevens((prev) => ({
        ...prev,
        vraag_tekst: null,
        kankersoort: null,
        vraag_type: null,
        samenvatting: null,
        bevestigd: false,
      }));
      setIntakeState("GEBRUIKER_TYPE");
    }
  };

  const handleMoreInfo = () => {
    addBotMessage(
      "Ik zoek aanvullende informatie voor u..."
    );
    // Re-run search with broader scope (same gegevens, just search again)
    setIntakeState("SEARCH");
    handleConfirm(true);
  };

  const handleNewTopic = () => {
    addBotMessage(
      "Prima, laten we een nieuw onderwerp bespreken.\n\n**Wat is uw vraag?**"
    );
    setGegevens((prev) => ({
      ...prev,
      vraag_tekst: null,
      kankersoort: null,
      vraag_type: null,
      samenvatting: null,
      bevestigd: false,
    }));
    setResultContent("");
    setIntakeState("VRAAG");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleVraagSubmit(e);
    }
  };

  // --- Render ---

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-72 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-700 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">IK</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-900">
                IKNL Infobot
              </h1>
              <p className="text-xs text-gray-500">
                Betrouwbare kankerinformatie
              </p>
            </div>
          </div>
        </div>

        {/* Progress indicator */}
        <div className="p-4 flex-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Voortgang
          </p>
          <div className="space-y-2">
            {[
              { state: "INTAKE_START", label: "AI-bekendheid" },
              { state: "GEBRUIKER_TYPE", label: "Type gebruiker" },
              { state: "VRAAG", label: "Uw vraag" },
              { state: "SAMENVATTING", label: "Bevestiging" },
              { state: "RESULTS", label: "Resultaten" },
            ].map((step, idx) => {
              const states: IntakeState[] = [
                "INTAKE_START",
                "GEBRUIKER_TYPE",
                "VRAAG",
                "SAMENVATTING",
                "RESULTS",
              ];
              const currentIdx = states.indexOf(intakeState);
              const stepIdx = states.indexOf(step.state as IntakeState);
              // SEARCH is between SAMENVATTING and RESULTS
              const adjustedCurrentIdx =
                intakeState === "SEARCH" ? states.indexOf("SAMENVATTING") + 0.5 : currentIdx;
              const isComplete = stepIdx < adjustedCurrentIdx;
              const isCurrent =
                step.state === intakeState ||
                (intakeState === "SEARCH" && step.state === "RESULTS");

              return (
                <div key={step.state} className="flex items-center gap-2">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                      isComplete
                        ? "bg-teal-600 text-white"
                        : isCurrent
                        ? "bg-teal-100 text-teal-700 border-2 border-teal-400"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {isComplete ? (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      isComplete
                        ? "text-teal-700 font-medium"
                        : isCurrent
                        ? "text-gray-900 font-medium"
                        : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-400 leading-relaxed">
            Deze chat is een prototype en geeft geen persoonlijk medisch
            advies. Raadpleeg altijd uw arts of specialist.
          </p>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-3 shrink-0">
          <span className="text-sm text-gray-600">
            Sessie: {currentSessionId.slice(0, 8)}...
          </span>
          {isLoading && (
            <span className="ml-auto text-xs text-teal-700 flex items-center gap-1">
              <span className="w-2 h-2 bg-teal-600 rounded-full animate-pulse" />
              {intakeState === "SEARCH"
                ? "Bronnen worden doorzocht..."
                : "Wordt verwerkt..."}
            </span>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((msg, idx) => (
              <ChatMessage
                key={msg.id || idx}
                message={msg}
                sessionId={currentSessionId}
                query={
                  msg.role === "assistant" && idx > 0
                    ? messages
                        .slice(0, idx)
                        .filter((m) => m.role === "user")
                        .pop()?.content
                    : undefined
                }
              />
            ))}

            {/* Interactive elements based on current state */}
            {intakeState === "INTAKE_START" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={BEKENDHEID_OPTIONS}
                  onSelect={handleBekendheid}
                />
              </div>
            )}

            {intakeState === "GEBRUIKER_TYPE" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={GEBRUIKER_OPTIONS}
                  onSelect={handleGebruikerType}
                  columns={2}
                />
              </div>
            )}

            {intakeState === "SAMENVATTING" && !isLoading && (
              <div className="ml-10">
                <IntakeButtons
                  options={[
                    { value: "ja", label: "Ja, dit klopt" },
                    { value: "nee", label: "Nee, ik wil iets aanpassen" },
                  ]}
                  onSelect={(v) => handleConfirm(v === "ja")}
                />
              </div>
            )}

            {intakeState === "RESULTS" && !isLoading && (
              <div className="ml-10">
                <ResultsList
                  content=""
                  onMoreInfo={handleMoreInfo}
                  onNewTopic={handleNewTopic}
                />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area — only shown during VRAAG state or RESULTS (for follow-up) */}
        {(intakeState === "VRAAG" || intakeState === "RESULTS") && (
          <div className="border-t border-gray-200 bg-white p-4 shrink-0">
            <form
              onSubmit={intakeState === "VRAAG" ? handleVraagSubmit : (e) => {
                e.preventDefault();
                const text = inputText.trim();
                if (!text) return;
                // Follow-up question — treat as new vraag_tekst
                setGegevens((prev) => ({
                  ...prev,
                  vraag_tekst: text,
                  kankersoort: null,
                  vraag_type: null,
                  samenvatting: null,
                  bevestigd: false,
                }));
                setInputText("");
                addUserMessage(text);
                setIntakeState("VRAAG");
                // Trigger summarize
                setIsLoading(true);
                summarizeQuestion(gegevens.gebruiker_type!, text)
                  .then((result) => {
                    setGegevens((prev) => ({
                      ...prev,
                      vraag_tekst: text,
                      samenvatting: result.samenvatting,
                      kankersoort: result.kankersoort === "geen" ? null : result.kankersoort,
                      vraag_type: result.vraag_type,
                    }));
                    const typeLabel =
                      GEBRUIKER_LABELS[gegevens.gebruiker_type!] || gegevens.gebruiker_type;
                    addBotMessage(
                      `Als ik het goed begrijp is dit uw vraag:\n\n` +
                        `> U bent een **${typeLabel}** en zoekt informatie over: *${result.samenvatting}*\n\n` +
                        `**Klopt dit?**`
                    );
                    setIntakeState("SAMENVATTING");
                  })
                  .catch(() => {
                    addBotMessage("Er is een fout opgetreden. Probeer het opnieuw.");
                  })
                  .finally(() => setIsLoading(false));
              }}
              className="max-w-3xl mx-auto flex gap-3"
            >
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  intakeState === "VRAAG"
                    ? gegevens.ai_bekendheid === "niet_bekend"
                      ? "Schrijf in één zin duidelijk uw vraag..."
                      : "Stel uw vraag over kanker..."
                    : "Stel een nieuwe vraag..."
                }
                rows={1}
                disabled={isLoading}
                className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={isLoading || !inputText.trim()}
                className="px-5 py-3 bg-teal-700 text-white text-sm font-medium rounded-xl hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <svg
                    className="w-5 h-5 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                )}
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend builds**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && pnpm build`
Expected: Build succeeds without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: rewrite page.tsx as intake state machine flow"
```

---

### Task 9: Integration smoke test

**Files:** None new — just verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run frontend build**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/frontend && pnpm build`
Expected: Build succeeds

- [ ] **Step 3: Start backend and verify health**

Run: `cd /home/ralph/Projects/Hackathon-BOM-IKNL/teams/team5/backend && timeout 10 uv run uvicorn main:app --port 8001 &` then `curl http://localhost:8001/api/health`
Expected: JSON response with `"status": "healthy"` or `"status": "degraded"`, new endpoints visible in FastAPI docs

- [ ] **Step 4: Final commit with all changes**

If any straggling files remain:

```bash
git add -A
git commit -m "feat: complete intake flow — state machine + structured search"
```
