"""
Intake module: structured summarize + search flow.

Replaces the free-form tool-use orchestrator with two focused operations:
1. summarize_question — single LLM call to summarize user intent
2. search_and_format — query connectors + LLM formatting of results
"""

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import litellm

from models import IntakeSummarizeResponse, SourceResult

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """A single Server-Sent Event."""
    event: str
    data: str


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


# ---------------------------------------------------------------------------
# Source priority tables (from spec)
# ---------------------------------------------------------------------------

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

_VRAAG_TYPE_CONNECTORS: dict[str, set[str]] = {
    "patient_info": {"kanker_nl", "publications"},
    "cijfers":      {"nkr_cijfers", "kanker_nl"},
    "regionaal":    {"cancer_atlas", "nkr_cijfers"},
    "onderzoek":    {"publications", "nkr_cijfers"},
    "breed":        {"kanker_nl", "nkr_cijfers", "cancer_atlas", "publications"},
}


def _select_connectors(gebruiker_type: str, vraag_type: str | None) -> list[str]:
    """Select and order connectors based on user type and question type."""
    relevant = _VRAAG_TYPE_CONNECTORS.get(vraag_type or "breed", _VRAAG_TYPE_CONNECTORS["breed"])
    priority = _TYPE_PRIORITY.get(gebruiker_type, _TYPE_PRIORITY["anders"])
    ordered = [c for c in priority if c in relevant]
    for c in relevant:
        if c not in ordered:
            ordered.append(c)
    return ordered


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
    message_id = str(uuid.uuid4())
    sources_tried: list[str] = []
    all_sources: list[dict] = []

    connector_order = _select_connectors(gebruiker_type, vraag_type)
    kanker_filter = kankersoort if kankersoort and kankersoort != "geen" else None

    for connector_name in connector_order:
        if connector_name not in connectors:
            continue

        connector = connectors[connector_name]
        sources_tried.append(connector_name)

        try:
            query_params: dict[str, Any] = {"query": vraag_tekst}
            if kanker_filter:
                if connector_name == "kanker_nl":
                    query_params["kankersoort"] = kanker_filter
                elif connector_name in ("nkr_cijfers", "cancer_atlas"):
                    query_params["cancer_type"] = kanker_filter

            result = await connector.query(**query_params)
            contributed = result.data is not None and result.data != {}

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
