import logging
import json
from src.state import FinancialGraphState, QAResult
from src.tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a meticulous financial report quality auditor.
Your job is to verify that a financial report is accurate, internally consistent, and free of hallucinations.

You must check:
1. **Metric Consistency**: All financial metrics mentioned in the report match the source data exactly.
2. **Numerical Accuracy**: No fabricated numbers or calculations that don't add up.
3. **Data Honesty**: The report doesn't claim data that wasn't provided (no hallucinations).
4. **Logical Coherence**: Trends and conclusions drawn are supported by the actual data.
5. **Completeness**: Key metrics from the source data are addressed in the report.

Respond with a JSON object matching this schema:
{
    "passed": true/false,
    "feedback": "detailed feedback text (empty if passed)",
    "missing_metrics": ["list of metric names not mentioned"],
    "hallucination_risks": ["list of potential hallucinations or unsupported claims"]
}

Rules:
- Be strict about numerical accuracy - any mismatch is a failure
- If financial data source is "error_fallback", flag the report for requiring disclaimer
- If the report makes bold claims without data support, flag as hallucination risk
- If all metrics are present and accurate, the report passes
"""


async def quality_controller_node(state: FinancialGraphState) -> FinancialGraphState:
    draft = state.get("analysis_draft", "")
    metrics = state.get("financial_metrics", {})
    iteration_count = state.get("iteration_count", 0)
    ticker = state.get("company_ticker", "Unknown")

    # Increment iteration count (cap at 3)
    iteration_count += 1
    max_iterations = 3

    logger.info(f"Quality controller: validating report for {ticker} (iteration {iteration_count})")

    # Prepare metrics data for validation
    metrics_dict = metrics if isinstance(metrics, dict) else {}

    # Check for data quality issues
    data_source = metrics_dict.get("source", "unknown")
    has_error = "error" in metrics_dict or data_source == "error_fallback"

    # Build context for LLM validation
    qa_context = {
        "ticker": ticker,
        "financial_metrics": {
            "revenue": metrics_dict.get("revenue"),
            "net_income": metrics_dict.get("net_income"),
            "pe_ratio": metrics_dict.get("pe_ratio"),
            "debt_to_equity": metrics_dict.get("debt_to_equity"),
            "company_name": metrics_dict.get("company_name", ticker),
            "currency": metrics_dict.get("currency", "USD"),
        },
        "data_source": data_source,
        "has_data_error": has_error,
        "max_iterations": max_iterations,
        "current_iteration": iteration_count,
    }

    draft_truncated = draft[:8000] + (f"\n\n[... truncated, total {len(draft)} chars ...]" if len(draft) > 8000 else "")
    user_prompt = f"""Validate the following financial report against the source data.

## Source Data
{json.dumps(qa_context, indent=2)}

## Report to Validate (total length: {len(draft)} chars)
---
{draft_truncated}
---

Respond with ONLY a valid JSON object matching the specified schema. No markdown, no extra text.
"""

    # Run LLM-based validation
    llm_tool = LLMTool()
    raw_response = llm_tool.call(
        user_prompt,
        cache_key=f"qa:{ticker}:{metrics_dict.get('revenue', 0):.0f}:{iteration_count}",
    )

    # Parse LLM JSON response
    logger.info(f"Quality controller: raw LLM response: {raw_response[:500]}")
    qa_result = _parse_qa_response(raw_response, iteration_count, max_iterations, has_error, draft)

    logger.info(
        f"Quality controller: QA {'PASSED' if qa_result.passed else 'FAILED'} "
        f"(feedback: {len(qa_result.feedback)} chars)"
    )

    if qa_result.passed:
        logger.info(f"Quality controller: report approved for {ticker}")
        return {
            **state,
            "qa_feedback": [],
            "qa_passed": True,
            "iteration_count": iteration_count,
            "final_report": draft,
        }
    else:
        logger.warning(
            f"Quality controller: iteration {iteration_count}/{max_iterations} feedback for {ticker}"
        )
        return {
            **state,
            "qa_feedback": [f"[Iteration {iteration_count}] {qa_result.feedback}"],
            "qa_passed": False,
            "iteration_count": iteration_count,
        }


def _parse_qa_response(
    raw_response: str,
    iteration_count: int,
    max_iterations: int,
    has_error: bool,
    draft: str,
) -> QAResult:
    """Parse and validate the LLM's QA response, with fallbacks."""
    # Try to parse as JSON
    try:
        # Extract JSON from possible markdown code blocks
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0] if "\n" in cleaned else cleaned

        parsed = json.loads(cleaned)
        
        # Check for standard schema
        passed = parsed.get("passed", None)
        feedback = parsed.get("feedback", "")
        
        # Handle alternative schemas from local LLMs
        if passed is None:
            # Check for validation_status alternative
            status = parsed.get("validation_status", "")
            if status in ["success", "passed", "approved"]:
                passed = True
            elif status in ["failed", "rejected", "error"]:
                passed = False
            # Check for errors array
            errors = parsed.get("errors", [])
            if isinstance(errors, list) and len(errors) > 0:
                passed = False
                if not feedback:
                    feedback = "; ".join(errors[:3])
            # Check for notes/comments as feedback
            if not feedback:
                notes = parsed.get("notes", "")
                if notes:
                    feedback = notes
        
        # Fallback to heuristic if still undetermined
        if passed is None:
            passed = len(draft) > 100 and not has_error
        
        result = QAResult(
            passed=passed,
            feedback=feedback,
            missing_metrics=parsed.get("missing_metrics", []),
            hallucination_risks=parsed.get("hallucination_risks", []),
        )

        # If no data errors but LLM says passed, confirm
        # If data errors exist, always require disclaimer at minimum
        if has_error and result.passed:
            result.passed = False
            result.feedback = (
                result.feedback + " Financial data had errors. "
                "Report must include a disclaimer about data limitations. "
                "Please regenerate with appropriate caveats."
            )

        return result

    except json.JSONDecodeError:
        logger.warning("Quality controller: failed to parse LLM JSON response, applying heuristic validation")
        pass

    # Fallback: heuristic validation if JSON parsing fails
    feedback_parts = []
    is_valid = True

    if not draft or len(draft) < 100:
        is_valid = False
        feedback_parts.append("Report draft is too short or empty.")

    if has_error:
        is_valid = False
        feedback_parts.append(
            "Financial data was unavailable. Report must include data limitation disclaimer."
        )

    if iteration_count >= max_iterations:
        is_valid = False
        feedback_parts.append(f"Maximum iteration limit ({max_iterations}) reached.")

    return QAResult(
        passed=is_valid,
        feedback="; ".join(feedback_parts) if feedback_parts else "LLM parsing failed, manual review recommended.",
        missing_metrics=[],
        hallucination_risks=[],
    )
