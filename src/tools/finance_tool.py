import logging
import os
import asyncio
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FinanceInput(BaseModel):
    ticker: str = Field(description="The stock ticker symbol")


class FinanceOutput(BaseModel):
    metrics: Dict[str, Any] = Field(description="Key financial metrics")
    source: Optional[str] = Field(default=None, description="Data source identifier")


class FinanceTool:
    """Herramienta de datos financieros usando yfinance con retry y async."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._cache: dict[str, FinanceOutput] = {}
        logger.info("FinanceTool initialized with yfinance backend")

    def _build_cache_key(self, input_data: FinanceInput) -> str:
        return f"finance:{input_data.ticker.upper().strip()}"

    def run(self, input_data: FinanceInput) -> FinanceOutput:
        cache_key = self._build_cache_key(input_data)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for ticker: {input_data.ticker}")
            return self._cache[cache_key]

        result = self._execute_with_retry(input_data)
        self._cache[cache_key] = result
        return result

    async def arun(self, input_data: FinanceInput) -> FinanceOutput:
        """Async wrapper that offloads blocking I/O to executor."""
        return await asyncio.to_thread(self.run, input_data)

    def _execute_with_retry(self, input_data: FinanceInput) -> FinanceOutput:
        """Fetches real financial data via yfinance with exponential backoff."""
        last_error = None
        ticker = input_data.ticker.upper().strip()

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching financial data for: {ticker} (attempt {attempt})")
                import yfinance as yf

                ticker_obj = yf.Ticker(ticker)

                # Fetch info with timeout
                info = ticker_obj.info or {}

                # Extract key metrics with fallbacks
                revenue = info.get("totalRevenue", 0)
                net_income = info.get("netIncomeToCommon", 0)
                pe_ratio = info.get("trailingPE", None)
                debt_to_equity = info.get("debtToEquity", None)
                fiscal_year = info.get("fiscalYearEnd", None)
                currency = info.get("currency", "USD")
                company_name = info.get("shortName", ticker)

                metrics = {
                    "revenue": float(revenue) if revenue else 0.0,
                    "net_income": float(net_income) if net_income else 0.0,
                    "pe_ratio": float(pe_ratio) if pe_ratio else None,
                    "debt_to_equity": float(debt_to_equity) if debt_to_equity else None,
                    "ticker": ticker,
                    "currency": currency,
                    "fiscal_year": int(fiscal_year) if fiscal_year else None,
                    "company_name": company_name,
                    "source": "yfinance",
                }

                logger.info(f"Retrieved metrics for {ticker} from yfinance")
                return FinanceOutput(metrics=metrics, source="yfinance")

            except ImportError:
                last_error = "yfinance not installed. Install with: pip install yfinance"
                logger.error(last_error)
                break

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Finance fetch attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Finance data retrieval failed after {self.max_retries} attempts for {ticker}: {e}"
                    )

        # Fallback: return partial metrics with error flag
        logger.warning(f"Returning fallback metrics for {ticker}")
        return FinanceOutput(
            metrics={
                "revenue": 0.0,
                "net_income": 0.0,
                "pe_ratio": None,
                "debt_to_equity": None,
                "ticker": ticker,
                "currency": "USD",
                "fiscal_year": None,
                "company_name": ticker,
                "source": "fallback_error",
                "error": str(last_error) if last_error else "Unknown error",
            },
            source="error_fallback",
        )
