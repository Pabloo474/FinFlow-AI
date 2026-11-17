import logging
import asyncio
from src.state import FinancialGraphState
from src.tools.research_tool import MarketResearchTool, ResearchInput

logger = logging.getLogger(__name__)


async def market_researcher_node(state: FinancialGraphState) -> FinancialGraphState:
    ticker = state.get("company_ticker", "")
    objective = state.get("target_objective", "")

    query = f"Latest news and macroeconomic trends for {ticker} regarding {objective}"

    logger.info(f"Market researcher: searching for '{query}'")

    research_tool = MarketResearchTool()
    research_input = ResearchInput(query=query)

    try:
        result = await research_tool.arun(research_input)
        news_list = result.results if hasattr(result, 'results') else []
        logger.info(f"Market researcher: retrieved {len(news_list)} news items")
        return {
            **state,
            "raw_news": news_list,
        }
    except Exception as e:
        error_msg = f"Market research failed: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "raw_news": [],
            "errors": [error_msg],
        }
