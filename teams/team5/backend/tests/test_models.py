"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from models import ChatRequest, ChartData, FeedbackEntry, SourceResult, Citation


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(
            message="What is breast cancer?",
            session_id="abc-123",
            profile="patient",
        )
        assert req.message == "What is breast cancer?"
        assert req.profile == "patient"
        assert req.history == []

    def test_invalid_profile_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                message="Hello",
                session_id="abc-123",
                profile="hacker",
            )


class TestSourceResult:
    def test_construction(self):
        result = SourceResult(
            data={"incidence": 12000},
            summary="Breast cancer incidence in 2023.",
            sources=[
                Citation(
                    url="https://nkr.nl/data",
                    title="NKR Data",
                    reliability="high",
                )
            ],
            visualizable=True,
        )
        assert result.visualizable is True
        assert len(result.sources) == 1
        assert result.sources[0].title == "NKR Data"

    def test_none_data(self):
        result = SourceResult(
            data=None,
            summary="No data found.",
            sources=[],
            visualizable=False,
        )
        assert result.data is None


class TestFeedbackEntry:
    def test_auto_timestamp(self):
        entry = FeedbackEntry(
            session_id="sess-1",
            message_id="msg-1",
            rating="positive",
            query="survival rates",
            sources_tried=["nkr", "kanker_nl"],
        )
        assert entry.timestamp is not None

    def test_explicit_timestamp_preserved(self):
        from datetime import datetime, timezone

        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        entry = FeedbackEntry(
            session_id="sess-1",
            message_id="msg-1",
            rating="negative",
            query="treatment options",
            sources_tried=["pubmed"],
            timestamp=ts,
        )
        assert entry.timestamp == ts


class TestChartData:
    def test_line_chart(self):
        chart = ChartData(
            type="line",
            title="Incidence over time",
            data=[{"year": 2020, "count": 100}, {"year": 2021, "count": 110}],
            x_key="year",
            y_key="count",
        )
        assert chart.type == "line"
        assert len(chart.data) == 2

    def test_bar_chart_with_unit(self):
        chart = ChartData(
            type="bar",
            title="Survival rate",
            data=[{"stage": "I", "rate": 0.95}],
            x_key="stage",
            y_key="rate",
            unit="%",
        )
        assert chart.unit == "%"

    def test_value_type(self):
        chart = ChartData(
            type="value",
            title="Total cases",
            data=[{"value": 5000}],
            x_key="label",
            y_key="value",
        )
        assert chart.type == "value"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            ChartData(
                type="pie",
                title="Invalid",
                data=[],
                x_key="x",
                y_key="y",
            )
