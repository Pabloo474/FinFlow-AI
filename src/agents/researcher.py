import logging
import asyncio
import os
from typing import Dict, Any, Optional

from src.state import FinancialGraphState
from src.tools.research_tool import MarketResearchTool, ResearchInput, ResearchOutput

logger = logging.getLogger(__name__)


def _resolve_company_info(ticker: str) -> Dict[str, str]:
    """
    Resuelve nombre real, sector e industria desde yfinance antes de investigar.
    
    Esto permite construir queries contextualizadas y no genéricas.
    """
    info: Dict[str, str] = {
        "company_name": ticker,
        "sector": "Technology",
        "industry": "N/A",
    }
    
    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker.upper().strip())
        data = ticker_obj.info or {}
        
        name = data.get("shortName") or data.get("longName") or ticker
        sector = data.get("sector") or "Technology"
        industry = data.get("industry") or "N/A"
        
        info["company_name"] = str(name).strip() if name else ticker
        info["sector"] = str(sector).strip() if sector else "Technology"
        info["industry"] = str(industry).strip() if industry else "N/A"
        
        logger.info(f"Resolved company info for {ticker}: name={info['company_name']}, sector={info['sector']}, industry={info['industry']}")
    except ImportError:
        logger.warning("yfinance not available for company info resolution")
    except Exception as e:
        logger.warning(f"Failed to resolve company info for {ticker}: {e}. Using defaults.")
    
    return info


def _map_research_to_state(research: ResearchOutput, ticker: str) -> Dict[str, Any]:
    """
    Mapea el ResearchOutput (categorizado) al formato del state para que
    el analista y report_writer puedan consumirlo fácilmente.
    """
    def _format_items(items: list, max_len: int = 15) -> list:
        result = []
        for i, item in enumerate(items[:max_len]):
            result.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
                "published_date": item.get("published_date"),
                "score": item.get("score", 0.0),
                "category": item.get("category", "general"),
            })
        return result
    
    return {
        "raw_news": _format_items(
            [
                *[{**item, "category": "news"} for item in research.news],
                *[{**item, "category": "earnings"} for item in research.earnings],
            ],
            max_len=30
        ),
        "research_categorized": {
            "news": _format_items(research.news, 15),
            "earnings": _format_items(research.earnings, 10),
            "sector_analysis": _format_items(research.sector_analysis, 10),
            "competitors": _format_items(research.competitors, 10),
            "sentiment": _format_items(research.sentiment, 10),
            "total_results": research.total_results,
        },
        "research_summary": {
            "total_sources": research.total_results,
            "categories_found": {
                "news": len(research.news),
                "earnings": len(research.earnings),
                "sector_analysis": len(research.sector_analysis),
                "competitors": len(research.competitors),
                "sentiment": len(research.sentiment),
            },
        },
    }


async def market_researcher_node(state: FinancialGraphState) -> FinancialGraphState:
    """
    Nodo de investigación de mercado mejorado.
    
    Mejoras:
    1. Resuelve company_name, sector, industry desde yfinance antes de buscar
    2. Usa ResearchInput correcto (ticker, company_name, sector)
    3. Almacena resultados categorizados en el state
    4. Mantiene raw_news backward-compatible con el pipeline existente
    """
    ticker = state.get("company_ticker", "")
    logger.info(f"Market researcher: starting advanced research for {ticker}")

    # Step 1: Resolve company info from yfinance
    company_info = _resolve_company_info(ticker)
    
    # Step 2: Build research input with real company context
    research_input = ResearchInput(
        ticker=ticker,
        company_name=company_info["company_name"],
        sector=company_info["sector"],
    )
    
    logger.info(
        f"Research input: ticker={research_input.ticker}, "
        f"name={research_input.company_name}, "
        f"sector={research_input.sector}"
    )

    # Step 3: Execute research with optimized settings
    research_tool = MarketResearchTool(
        max_retries=3,
        cache_enabled=True,
        days_back=90,
    )

    try:
        research = await research_tool.arun(research_input)
        
        logger.info(
            f"Research complete for {ticker}: "
            f"{research.total_results} total results | "
            f"news={len(research.news)}, earnings={len(research.earnings)}, "
            f"sector={len(research.sector_analysis)}, "
            f"competitors={len(research.competitors)}, "
            f"sentiment={len(research.sentiment)}"
        )
        
        # Step 4: Map to state format
        state_updates = _map_research_to_state(research, ticker)
        state_updates["company_info"] = company_info
        
        return {
            **state,
            **state_updates,
        }
        
    except Exception as e:
        error_msg = f"Market research failed for {ticker}: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "raw_news": [],
            "research_categorized": {
                "news": [],
                "earnings": [],
                "sector_analysis": [],
                "competitors": [],
                "sentiment": [],
                "total_results": 0,
            },
            "research_summary": {
                "total_sources": 0,
                "categories_found": {"news": 0, "earnings": 0, "sector_analysis": 0, "competitors": 0, "sentiment": 0},
            },
            "errors": [error_msg],
        }
