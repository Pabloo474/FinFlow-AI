import logging
import json
from src.state import FinancialGraphState, FinancialMetricsModel
from src.tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert financial analyst and report writer.
Your task is to synthesize market research findings and financial metrics into a comprehensive, professional financial analysis report.

Guidelines:
- Write in a clear, structured format with appropriate markdown headings
- Analyze and interpret the data, don't just list it
- Highlight key trends, risks, and opportunities
- Compare metrics to industry context when possible
- Use a professional, executive-appropriate tone
- Be specific and quantitative when data is available
- Acknowledge data limitations when metrics are missing or flagged as errors
- The report should be detailed, thorough, and actionable

    Format the report with these sections:
    1. Executive Summary
    2. Company Overview
    3. Market Research & News Analysis
    4. Financial Performance Analysis
    5. Key Metrics Breakdown
    6. Risks & Challenges
    7. Conclusion & Outlook
    8. References (Include a list of the news titles and sources used in the analysis)
    """


async def report_writer_node(state: FinancialGraphState) -> FinancialGraphState:
    news = state.get("raw_news", [])
    metrics = state.get("financial_metrics", {})
    ticker = state.get("company_ticker", "Unknown")
    objective = state.get("target_objective", "No objective provided")
    errors = state.get("errors", [])

    logger.info(f"Report writer: generating report for {ticker}")

    # Prepare structured data for LLM
    metrics_dict = metrics if isinstance(metrics, dict) else {}
    news_items = news if isinstance(news, list) else []

    # Build context for the LLM
    context = {
        "ticker": ticker,
        "objective": objective,
        "company_name": metrics_dict.get("company_name", ticker),
        "currency": metrics_dict.get("currency", "USD"),
        "fiscal_year": metrics_dict.get("fiscal_year"),
        "metrics": {
            "revenue": metrics_dict.get("revenue"),
            "net_income": metrics_dict.get("net_income"),
            "pe_ratio": metrics_dict.get("pe_ratio"),
            "debt_to_equity": metrics_dict.get("debt_to_equity"),
        },
        "news_sources": [
            {
                "title": (item.get("title", "N/A") if isinstance(item, dict) else "N/A")[:120],
                "content": (item.get("content", "N/A")[:150] if isinstance(item, dict) else "N/A"),
            }
            for item in news_items[:3]
        ],
        "data_quality_flags": [],
    }

    # Check data quality
    if metrics_dict.get("source") == "error_fallback" or "error" in metrics_dict:
        context["data_quality_flags"].append(
            "Financial data was unavailable and fell back to error state. Report should note this limitation."
        )
    if not news_items:
        context["data_quality_flags"].append("No news data available for market analysis.")

    # Build the user prompt
    user_prompt = f"""Generate a comprehensive financial analysis report for {ticker}.

## Objective
{objective}

## Context Data (JSON)
{json.dumps(context, indent=2)}
"""

    # Generate report using LLM
    llm_tool = LLMTool()
    draft = llm_tool.call_with_system_prompt(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        cache_key=f"report:{ticker}:{len(news_items)}:{metrics_dict.get('revenue', 0):.0f}",
    )

    if errors:
        context["previous_errors"] = errors
        logger.warning(f"Report writer: incorporating {len(errors)} previous error context")

    logger.info(f"Report writer: draft generated ({len(draft)} characters)")
    return {
        **state,
        "analysis_draft": draft,
    }
