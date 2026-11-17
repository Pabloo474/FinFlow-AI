import logging
import asyncio
from src.state import FinancialGraphState
from src.tools.finance_tool import FinanceTool, FinanceInput

logger = logging.getLogger(__name__)


async def financial_analyst_node(state: FinancialGraphState) -> FinancialGraphState:
    ticker = state.get("company_ticker", "")

    logger.info(f"Financial analyst: fetching data for ticker '{ticker}'")

    finance_tool = FinanceTool()
    finance_input = FinanceInput(ticker=ticker)

    try:
        result = await finance_tool.arun(finance_input)
        metrics = result.metrics if hasattr(result, 'metrics') else {}

        source = result.source if hasattr(result, 'source') else "unknown"
        logger.info(f"Financial analyst: retrieved metrics from {source}")

        return {
            **state,
            "financial_metrics": metrics,
        }
    except Exception as e:
        error_msg = f"Financial analysis failed: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "financial_metrics": {"error": str(e), "ticker": ticker},
            "errors": [error_msg],
        }
