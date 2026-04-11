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
