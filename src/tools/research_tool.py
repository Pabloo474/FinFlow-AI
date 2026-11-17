import logging
import os
import asyncio
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from tavily import TavilyClient

from src.state import NewsItemModel

logger = logging.getLogger(__name__)


class ResearchInput(BaseModel):
    query: str = Field(description="The search query for market research")


class ResearchOutput(BaseModel):
    results: List[Dict[str, Any]] = Field(
        description="List of search results with content and URL"
    )


class MarketResearchTool:
    """Herramienta de investigación de mercado usando Tavily API con retry y async."""

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.max_retries = max_retries
        self._client: Optional[TavilyClient] = None
        self._cache: dict[str, ResearchOutput] = {}
        logger.info("MarketResearchTool initialized")

    @property
    def client(self) -> TavilyClient:
        if self._client is None:
            if not self.api_key:
                raise ValueError("TAVILY_API_KEY environment variable is required")
            self._client = TavilyClient(api_key=self.api_key)
        return self._client

    def _build_cache_key(self, input_data: ResearchInput) -> str:
        return f"research:{input_data.query}"

    def run(self, input_data: ResearchInput) -> ResearchOutput:
        cache_key = self._build_cache_key(input_data)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for query: {input_data.query[:50]}...")
            return self._cache[cache_key]

        result = self._execute_with_retry(input_data)
        self._cache[cache_key] = result
        return result

    async def arun(self, input_data: ResearchInput) -> ResearchOutput:
        """Async wrapper that offloads blocking I/O to executor."""
        return await asyncio.to_thread(self.run, input_data)

    def _execute_with_retry(self, input_data: ResearchInput) -> ResearchOutput:
        """Executes Tavily search with exponential backoff retry."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Searching for: {input_data.query} (attempt {attempt})")
                search_result = self.client.search(
                    query=input_data.query,
                    search_depth="basic",
                    max_results=3,
                )

                formatted_results = []
                for result in search_result.get("results", []):
                    try:
                        item = NewsItemModel(
                            title=result.get("title", "No title"),
                            content=result.get("content", "No content"),
                            url=result.get("url", ""),
                            published_date=result.get("published_date", None),
                        )
                        formatted_results.append(item.model_dump())
                    except Exception as e:
                        logger.warning(f"Failed to parse news item: {e}")
                        continue

                logger.info(f"Found {len(formatted_results)} news items")
                return ResearchOutput(results=formatted_results)

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Research attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Research failed after {self.max_retries} attempts: {e}"
                    )

        return ResearchOutput(results=[{
            "title": "Research Error",
            "content": f"Failed to retrieve news after {self.max_retries} attempts: {str(last_error)}",
            "url": "",
            "published_date": None,
        }])
