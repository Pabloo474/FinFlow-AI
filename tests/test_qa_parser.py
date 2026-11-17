"""Tests for _parse_qa_response logic."""
import pytest
from src.agents.quality_controller import _parse_qa_response


class TestQAParser:
    """Test QA response parsing with various LLM output formats."""

    def test_parse_standard_json(self):
        """Should parse standard JSON with 'passed' field."""
        response = '{"passed": true, "feedback": "", "missing_metrics": [], "hallucination_risks": []}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.passed is True

    def test_parse_standard_json_failed(self):
        """Should parse failed validation."""
        response = '{"passed": false, "feedback": "Fix revenue section", "missing_metrics": ["revenue"]}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.passed is False
        assert result.feedback == "Fix revenue section"

    def test_parse_markdown_code_block(self):
        """Should extract JSON from markdown code blocks."""
        response = '```json\n{"passed": true, "feedback": ""}\n```'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.passed is True

    def test_parse_validation_status_schema(self):
        """Should handle validation_status alternative schema."""
        response = '{"validation_status": "success", "notes": "Looks good"}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.passed is True

    def test_parse_validation_status_failed(self):
        """Should handle failed validation status."""
        response = '{"validation_status": "failed", "errors": ["Missing P/E ratio"]}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.passed is False

    def test_parse_with_hallucination_risks(self):
        """Should extract hallucination risks."""
        response = '{"passed": false, "feedback": "Check numbers", "hallucination_risks": ["Claim about 50% growth unsupported"]}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert "Claim about 50% growth unsupported" in result.hallucination_risks

    def test_parse_invalid_json_fallback(self):
        """Should fallback to heuristic when JSON is invalid."""
        response = "This is not JSON at all"
        result = _parse_qa_response(
            response, 1, 3, False,
            "A proper report with enough content to pass the heuristic check for length"
        )
        assert result.passed is True

    def test_parse_invalid_json_short_draft(self):
        """Should fail heuristic for short drafts."""
        response = "Not JSON"
        result = _parse_qa_response(response, 1, 3, False, "Short")
        assert result.passed is False

    def test_has_error_forces_rejection(self):
        """Should force rejection when data has errors even if LLM says passed."""
        response = '{"passed": true, "feedback": ""}'
        result = _parse_qa_response(response, 1, 3, True, "Test report")
        assert result.passed is False
        assert "data limitations" in result.feedback.lower()

    def test_max_iterations_forces_rejection(self):
        """Should reject when max iterations reached."""
        response = '{"passed": false, "feedback": "Keep fixing"}'
        result = _parse_qa_response(
            response, 3, 3, False,
            "A detailed report with sufficient content to pass length check"
        )
        assert result.passed is False

    def test_empty_feedback_default(self):
        """Should handle empty feedback gracefully."""
        response = '{"passed": true, "feedback": "", "missing_metrics": [], "hallucination_risks": []}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert result.feedback == ""

    def test_notes_as_feedback(self):
        """Should use 'notes' field as feedback when present."""
        response = '{"validation_status": "success", "notes": "Minor improvements suggested"}'
        result = _parse_qa_response(response, 1, 3, False, "Test report")
        assert "Minor improvements suggested" in result.feedback
