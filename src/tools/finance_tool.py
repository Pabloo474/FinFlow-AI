import logging
import os
import asyncio
import time
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FinanceInput(BaseModel):
    ticker: str = Field(description="The stock ticker symbol")


class FinanceOutput(BaseModel):
    metrics: Dict[str, Any] = Field(description="Key financial metrics")
    source: Optional[str] = Field(default=None, description="Data source identifier")


class FinanceTool:
    """
    Herramienta avanzada de datos financieros usando yfinance.

    Métricas expandidas:
    - Valuation: P/E, P/B, P/S, EV/EBITDA, PEG
    - Profitability: márgenes (gross, operating, net), ROE, ROA, ROIC
    - Growth: revenue, earnings, dividend growth rates
    - Financial health: deuda, liquidez, cobertura de intereses
    - Cash flow: OCF, Free Cash Flow, capex
    - Technical: precio actual, rango 52 semanas, volatilidad
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._cache: dict[str, FinanceOutput] = {}
        logger.info("Advanced FinanceTool initialized with yfinance backend")

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
        """Fetches comprehensive financial data via yfinance with exponential backoff."""
        last_error = None
        ticker = input_data.ticker.upper().strip()

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching financial data for: {ticker} (attempt {attempt})")
                import yfinance as yf

                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info or {}

                # --- VALUATION METRICS ---
                pe_ratio = info.get("trailingPE")
                forward_pe = info.get("forwardPE")
                price_to_book = info.get("priceToBook")
                price_to_sales = info.get("priceToSalesTrailing12Months")
                enterprise_value = info.get("enterpriseValue")

                # Calculate EV/EBITDA (if data available)
                ebitda = info.get("ebitda")
                ev_ebitda = None
                if enterprise_value and ebitda:
                    ev_ebitda = enterprise_value / ebitda if ebitda != 0 else None

                # --- PROFITABILITY METRICS ---
                gross_margin = info.get("grossMargins")
                operating_margin = info.get("operatingMargins")
                profit_margin = info.get("profitMargins")
                return_on_equity = info.get("returnOnEquity")
                return_on_assets = info.get("returnOnAssets")
                return_on_investment = info.get("returnOnInvestment")

                # --- GROWTH METRICS ---
                revenue_growth = info.get("revenueGrowth")
                earnings_growth = info.get("earningsGrowth")
                revenue_per_share = info.get("revenuePerShare")
                earnings_quarterly_growth = info.get("earningsQuarterlyGrowth")

                # --- FINANCIAL HEALTH ---
                total_revenue = info.get("totalRevenue")
                net_income_to_common = info.get("netIncomeToCommon")
                diluted_eps = info.get("dilutedEps")
                quick_ratio = info.get("quickRatio")
                current_ratio = info.get("currentRatio")
                debt_to_equity = info.get("debtToEquity")
                total_debt = info.get("totalDebt")
                total_cash = info.get("totalCash")
                interest_coverage = info.get("interestCoverage")

                # --- CASH FLOW METRICS ---
                operating_cashflow = info.get("operatingCashflow")
                free_cashflow = info.get("freeCashflow")
                capital_expenditures = info.get("capitalExpenditures")

                # --- TECHNICAL / MARKET DATA ---
                current_price = info.get("currentPrice")
                target_mean_price = info.get("targetMeanPrice")
                target_high_price = info.get("targetHighPrice")
                target_low_price = info.get("targetLowPrice")
                target_median_price = info.get("targetMedianPrice")
                number_of_analyst_opinions = info.get("numberOfAnalystOpinions")
                fifty_day_average = info.get("fiftyDayAverage")
                two_hundred_day_average = info.get("twoHundredDayAverage")
                fifty_two_week_high = info.get("fiftyTwoWeekHigh")
                fifty_two_week_low = info.get("fiftyTwoWeekLow")
                market_cap = info.get("marketCap")
                beta = info.get("beta")
                volume = info.get("volume")
                average_volume = info.get("averageVolume")
                dividend_rate = info.get("dividendRate")
                dividend_yield = info.get("dividendYield")
                payout_ratio = info.get("payoutRatio")
                five_year_avg_div_yield = info.get("fiveYearAvgDividendYield")

                fiscal_year = info.get("fiscalYearEnd")
                currency = info.get("currency", "USD")
                company_name = info.get("shortName", ticker)
                sector = info.get("sector", "N/A")
                industry = info.get("industry", "N/A")
                full_time_employees = info.get("fullTimeEmployees")

                # Build comprehensive metrics dictionary
                metrics = {
                    # Basic info
                    "ticker": ticker,
                    "company_name": company_name,
                    "sector": sector,
                    "industry": industry,
                    "currency": currency,
                    "fiscal_year": int(fiscal_year) if fiscal_year else None,
                    "employees": full_time_employees,

                    # Valuation
                    "market_cap": float(market_cap) if market_cap else None,
                    "pe_ratio": float(pe_ratio) if pe_ratio else None,
                    "forward_pe": float(forward_pe) if forward_pe else None,
                    "price_to_book": float(price_to_book) if price_to_book else None,
                    "price_to_sales": float(price_to_sales) if price_to_sales else None,
                    "ev_ebitda": float(ev_ebitda) if ev_ebitda else None,
                    "diluted_eps": float(diluted_eps) if diluted_eps else None,

                    # Profitability
                    "gross_margin": float(gross_margin * 100) if gross_margin else None,
                    "operating_margin": float(operating_margin * 100) if operating_margin else None,
                    "profit_margin": float(profit_margin * 100) if profit_margin else None,
                    "return_on_equity": float(return_on_equity * 100) if return_on_equity else None,
                    "return_on_assets": float(return_on_assets * 100) if return_on_assets else None,
                    "return_on_investment": float(return_on_investment * 100) if return_on_investment else None,

                    # Growth
                    "revenue_growth": float(revenue_growth * 100) if revenue_growth else None,
                    "earnings_growth": float(earnings_growth * 100) if earnings_growth else None,
                    "revenue_per_share": float(revenue_per_share) if revenue_per_share else None,
                    "earnings_quarterly_growth": float(earnings_quarterly_growth * 100) if earnings_quarterly_growth else None,

                    # Financial health
                    "total_revenue": float(total_revenue) if total_revenue else None,
                    "net_income": float(net_income_to_common) if net_income_to_common else None,
                    "quick_ratio": float(quick_ratio) if quick_ratio else None,
                    "current_ratio": float(current_ratio) if current_ratio else None,
                    "debt_to_equity": float(debt_to_equity) if debt_to_equity else None,
                    "total_debt": float(total_debt) if total_debt else None,
                    "total_cash": float(total_cash) if total_cash else None,
                    "interest_coverage": float(interest_coverage) if interest_coverage else None,

                    # Cash flow
                    "operating_cashflow": float(operating_cashflow) if operating_cashflow else None,
                    "free_cashflow": float(free_cashflow) if free_cashflow else None,
                    "capital_expenditures": float(capital_expenditures) if capital_expenditures else None,

                    # Technical / Market
                    "current_price": float(current_price) if current_price else None,
                    "fifty_day_average": float(fifty_day_average) if fifty_day_average else None,
                    "two_hundred_day_average": float(two_hundred_day_average) if two_hundred_day_average else None,
                    "fifty_two_week_high": float(fifty_two_week_high) if fifty_two_week_high else None,
                    "fifty_two_week_low": float(fifty_two_week_low) if fifty_two_week_low else None,
                    "beta": float(beta) if beta else None,
                    "volume": int(volume) if volume else None,
                    "average_volume": int(average_volume) if average_volume else None,

                    # Analyst targets
                    "analyst_target_mean": float(target_mean_price) if target_mean_price else None,
                    "analyst_target_high": float(target_high_price) if target_high_price else None,
                    "analyst_target_low": float(target_low_price) if target_low_price else None,
                    "analyst_target_median": float(target_median_price) if target_median_price else None,
                    "analyst_opinions_count": int(number_of_analyst_opinions) if number_of_analyst_opinions else None,

                    # Dividends
                    "dividend_yield": float(dividend_yield * 100) if dividend_yield else None,
                    "dividend_rate": float(dividend_rate) if dividend_rate else None,
                    "payout_ratio": float(payout_ratio * 100) if payout_ratio else None,
                    "five_year_avg_div_yield": float(five_year_avg_div_yield * 100) if five_year_avg_div_yield else None,

                    # Source
                    "source": "yfinance",
                }

                logger.info(f"Retrieved comprehensive metrics for {ticker} from yfinance")
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
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Finance data retrieval failed after {self.max_retries} attempts for {ticker}: {e}"
                    )

        # Fallback: return partial metrics with error flag
        logger.warning(f"Returning fallback metrics for {ticker}")
        return FinanceOutput(
            metrics={
                "ticker": ticker,
                "company_name": ticker,
                "sector": "N/A",
                "industry": "N/A",
                "currency": "USD",
                "fiscal_year": None,
                "employees": None,
                "market_cap": None,
                "pe_ratio": None,
                "forward_pe": None,
                "price_to_book": None,
                "price_to_sales": None,
                "ev_ebitda": None,
                "diluted_eps": None,
                "gross_margin": None,
                "operating_margin": None,
                "profit_margin": None,
                "return_on_equity": None,
                "return_on_assets": None,
                "return_on_investment": None,
                "revenue_growth": None,
                "earnings_growth": None,
                "revenue_per_share": None,
                "earnings_quarterly_growth": None,
                "total_revenue": None,
                "net_income": None,
                "quick_ratio": None,
                "current_ratio": None,
                "debt_to_equity": None,
                "total_debt": None,
                "total_cash": None,
                "interest_coverage": None,
                "operating_cashflow": None,
                "free_cashflow": None,
                "capital_expenditures": None,
                "current_price": None,
                "fifty_day_average": None,
                "two_hundred_day_average": None,
                "fifty_two_week_high": None,
                "fifty_two_week_low": None,
                "beta": None,
                "volume": None,
                "average_volume": None,
                "analyst_target_mean": None,
                "analyst_target_high": None,
                "analyst_target_low": None,
                "analyst_target_median": None,
                "analyst_opinions_count": None,
                "dividend_yield": None,
                "dividend_rate": None,
                "payout_ratio": None,
                "five_year_avg_div_yield": None,
                "source": "error_fallback",
                "error": str(last_error) if last_error else "Unknown error",
            },
            source="error_fallback",
        )
