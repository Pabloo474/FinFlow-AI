"""Tests for Pydantic contracts and state definitions."""
import json
import pytest
from src.state import (
    FinancialMetricsModel,
    NewsItemModel,
    QAResult,
    FinancialGraphState,
)


class TestFinancialMetricsModel:
    """Test FinancialMetricsModel Pydantic contract."""

    def test_valid_metrics(self):
        """Should accept valid metrics."""
        metrics = FinancialMetricsModel(
            revenue=394328000000,
            net_income=99803000000,
            pe_ratio=31.5,
            debt_to_equity=1.87,
            ticker="AAPL",
        )
        assert metrics.revenue == 394328000000
        assert metrics.pe_ratio == 31.5
        assert metrics.ticker == "AAPL"

    def test_optional_fields_default_none(self):
        """Optional fields should default to None."""
        metrics = FinancialMetricsModel(
            revenue=1000000,
            net_income=500000,
        )
        assert metrics.pe_ratio is None
        assert metrics.debt_to_equity is None

    def test_to_display_dict(self):
        """Should format metrics for display."""
        metrics = FinancialMetricsModel(
            revenue=394328000000,
            net_income=99803000000,
            pe_ratio=31.5,
            debt_to_equity=1.87,
        )
        display = metrics.to_display_dict()
        assert display["Revenue"] == "$394,328,000,000"
        assert display["Net Income"] == "$99,803,000,000"
        assert display["P/E Ratio"] == "31.50"
        assert display["Debt/Equity"] == "1.87"

    def test_to_display_dict_excludes_none(self):
        """Should exclude None fields from display dict."""
        metrics = FinancialMetricsModel(
            revenue=1000000,
            net_income=500000,
        )
        display = metrics.to_display_dict()
        assert "P/E Ratio" not in display
        assert "Debt/Equity" not in display


class TestNewsItemModel:
    """Test NewsItemModel Pydantic contract."""

    def test_valid_news_item(self):
        """Should accept valid news item."""
        news = NewsItemModel(
            title="Apple Reports Q4 Earnings",
            content="Apple announced strong quarterly results...",
            url="https://example.com/article",
        )
        assert news.title == "Apple Reports Q4 Earnings"
        assert news.url == "https://example.com/article"

    def test_news_item_with_date(self):
        """Should accept published date."""
        news = NewsItemModel(
            title="Test",
            content="Content",
            url="https://example.com",
            published_date="2024-10-15",
        )
        assert news.published_date == "2024-10-15"


class TestQAResult:
    """Test QAResult Pydantic contract."""

    def test_passed_result(self):
        """Should accept passed result."""
        qa = QAResult(
            passed=True,
            feedback="",
        )
        assert qa.passed is True
        assert qa.missing_metrics == []

    def test_failed_result(self):
        """Should accept failed result with feedback."""
        qa = QAResult(
            passed=False,
            feedback="Missing revenue analysis",
            missing_metrics=["revenue"],
            hallucination_risks=[],
        )
        assert qa.passed is False
        assert "revenue" in qa.missing_metrics
