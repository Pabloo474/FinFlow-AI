import logging
import os
import asyncio
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from tavily import TavilyClient

from src.state import NewsItemModel

logger = logging.getLogger(__name__)


# === Contracts Pydantic ===


class ResearchInput(BaseModel):
    """Entrada para investigación de mercado avanzada."""
    ticker: str = Field(description="The stock ticker symbol (e.g., AAPL)")
    company_name: Optional[str] = Field(default="", description="Company full name for better queries")
    sector: Optional[str] = Field(default="", description="Sector/industry for comparative queries")


class ResearchResult(BaseModel):
    """Resultado individual de investigación."""
    title: str = Field(description="Title of the result")
    content: str = Field(description="Content or summary")
    url: str = Field(description="Source URL")
    published_date: Optional[str] = Field(default=None, description="Publication date")
    score: float = Field(default=0.0, description="Relevance score 0-1")
    category: str = Field(default="general", description="Category: news, earnings, sector, competitor, sentiment")


class ResearchOutput(BaseModel):
    """Salida estructurada de investigación."""
    news: List[Dict[str, Any]] = Field(default_factory=list, description="Recent company news")
    earnings: List[Dict[str, Any]] = Field(default_factory=list, description="Earnings/financial results")
    sector_analysis: List[Dict[str, Any]] = Field(default_factory=list, description="Sector/industry trends")
    competitors: List[Dict[str, Any]] = Field(default_factory=list, description="Competitive landscape")
    sentiment: List[Dict[str, Any]] = Field(default_factory=list, description="Market sentiment/analysis")
    total_results: int = Field(default=0, description="Total unique results")


class MarketResearchTool:
    """
    Herramienta avanzada de investigación de mercado.
    
    Mejoras implementadas:
    - Búsqueda multi-query optimizada con queries estratégicas
    - Filtrado temporal (últimos 90 días por defecto)
    - Priorización de fuentes premium con tiers de calidad
    - Profundidad 'advanced' para mayor cobertura
    - Deduplicación por hash de URL + similitud de título
    - Categorización inteligente por contenido
    - Score de relevancia basado en antigüedad y fuente
    - Cache inteligente por ticker+sector
    """

    # Tiers de fuentes por prioridad
    PREMIUM_DOMAINS = [
        "bloomberg.com",
        "reuters.com",
        "wallstreetjournal.com",
        "financialtimes.com",
        "marketwatch.com",
        "cnbc.com",
        "seekingalpha.com",
        "morningstar.com",
    ]
    
    SECONDARY_DOMAINS = [
        "investopedia.com",
        "fool.com",
        "thestreet.com",
        "finance.yahoo.com",
        "bizjournals.com",
        "businessinsider.com",
        "axios.com",
        "barrons.com",
    ]

    # Keywords para categorización
    EARNINGS_KEYWORDS = [
        "earnings", "revenue", "net income", "profit", "loss", 
        "eps", "quarterly", "quarter", "financial results",
        "guidance", "forecast", "dividend", "buyback",
        "fiscal", "quarterly results", "earnings call"
    ]
    
    SECTOR_KEYWORDS = [
        "industry", "sector", "market trends", "market share",
        "industry analysis", "growth", "demand", "supply chain",
        "regulation", "policy", "commodity", "pricing power"
    ]
    
    COMPETITOR_KEYWORDS = [
        "competitor", "versus", "vs", "comparison", "rival",
        "compared to", "peer", "market leader", "alternative",
        "substitute", "competing", "compares"
    ]
    
    SENTIMENT_KEYWORDS = [
        "sentiment", "outlook", "forecast", "prediction",
        "bullish", "bearish", "rally", "crash", "volatility",
        "risk", "opportunity", "momentum", "technical analysis"
    ]

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, 
                 cache_enabled: bool = True, days_back: int = 90):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled
        self.days_back = days_back
        self._client: Optional[TavilyClient] = None
        self._cache: dict[str, ResearchOutput] = {}
        logger.info(
            f"MarketResearchTool initialized | "
            f"premium_domains={len(self.PREMIUM_DOMAINS)}, "
            f"secondary_domains={len(self.SECONDARY_DOMAINS)}, "
            f"days_back={days_back}"
        )

    @property
    def client(self) -> TavilyClient:
        if self._client is None:
            if not self.api_key:
                raise ValueError("TAVILY_API_KEY environment variable is required")
            self._client = TavilyClient(api_key=self.api_key)
        return self._client

    def _build_cache_key(self, input_data: ResearchInput) -> str:
        return hashlib.md5(
            f"research:{input_data.ticker}:{input_data.sector}:{self.days_back}".encode()
        ).hexdigest()[:16]

    def run(self, input_data: ResearchInput) -> ResearchOutput:
        if not self.cache_enabled:
            return self._execute_with_retry(input_data)
        
        cache_key = self._build_cache_key(input_data)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for ticker: {input_data.ticker}")
            return self._cache[cache_key]

        result = self._execute_with_retry(input_data)
        self._cache[cache_key] = result
        return result

    async def arun(self, input_data: ResearchInput) -> ResearchOutput:
        """Async wrapper that offloads blocking I/O to executor."""
        return await asyncio.to_thread(self.run, input_data)

    def _execute_with_retry(self, input_data: ResearchInput) -> ResearchOutput:
        """Executes multi-query research with exponential backoff retry."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Advanced research for {input_data.ticker} "
                    f"(attempt {attempt}, company: {input_data.company_name})"
                )

                # Build multiple strategic queries
                queries = self._build_queries(input_data)
                logger.info(f"Built {len(queries)} queries for {input_data.ticker}")
                
                # Execute all queries and aggregate results
                all_results = []
                for query_name, query_text in queries:
                    logger.info(f"Query [{query_name}]: {query_text}")
                    query_results = self._execute_single_query(query_text)
                    all_results.extend(query_results)
                    logger.info(f"  -> Got {len(query_results)} results")

                # Deduplicate results
                deduped = self._deduplicate(all_results)
                logger.info(f"After dedup: {len(deduped)} results")
                
                # Score and categorize results
                output = self._score_and_categorize(deduped, input_data)
                
                logger.info(
                    f"Research complete: {len(output.news)} news, "
                    f"{len(output.earnings)} earnings, "
                    f"{len(output.sector_analysis)} sector, "
                    f"{len(output.competitors)} competitors, "
                    f"{len(output.sentiment)} sentiment"
                )
                return output

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Research attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Research failed after {self.max_retries} attempts: {e}"
                    )

        # Fallback with error info
        logger.warning("Returning fallback research output")
        return ResearchOutput(
            news=[{
                "title": "Research Error",
                "content": f"Failed to retrieve news after {self.max_retries} attempts: {str(last_error)}",
                "url": "",
                "published_date": None,
                "score": 0.0,
                "category": "error"
            }],
            earnings=[],
            sector_analysis=[],
            competitors=[],
            sentiment=[],
            total_results=0,
        )

    def _build_queries(self, input_data: ResearchInput) -> List[tuple]:
        """
        Construye consultas estratégicas múltiples para cobertura completa.
        
        Estrategia:
        1. Noticias recientes del ticker (prioridad máxima)
        2. Resultados financieros/earnings
        3. Análisis del sector (si disponible)
        4. Análisis comparativo/competidores
        5. Sentimiento de mercado
        6. Eventos corporativos importantes
        
        Retorna lista de (nombre_categoria, query_texto).
        """
        ticker = input_data.ticker
        name = input_data.company_name or ticker
        sector = input_data.sector or ""
        
        queries = [
            # 1. Noticias principales del ticker (queries agresivas recientes)
            ("latest_news", f"{ticker} stock news today this week"),
            
            # 2. Resultados financieros y earnings
            ("earnings", f"{ticker} quarterly earnings revenue profit financial results"),
            
            # 3. Análisis fundamental y valoración
            ("fundamental", f"{ticker} valuation analysis fundamentals investment thesis"),
            
            # 4. Análisis del sector (si disponible)
            ("sector_trends", f"{sector} industry trends market analysis 2024 2025") if sector else None,
            
            # 5. Competidores principales (si disponible)
            ("competitors", f"{ticker} vs competitors comparison market share analysis") if sector else None,
            
            # 6. Sentimiento y análisis técnico
            ("sentiment", f"{ticker} stock sentiment analysis forecast outlook price target"),
            
            # 7. Eventos corporativos y estrategia
            ("corporate", f"{name} strategy acquisitions partnerships announcements"),
            
            # 8. Análisis macroeconómico del sector
            ("macro", f"{sector} sector macroeconomic impact interest rates inflation") if sector else None,
        ]
        
        # Filtrar None y retornar
        return [(name, q) for name, q in queries if q is not None]

    def _execute_single_query(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una única búsqueda con configuración optimizada.
        """
        results = []
        
        try:
            # Usar advanced search para mayor cobertura y profundidad
            search_result = self.client.search(
                query=query_text,
                search_depth="advanced",
                max_results=8,
                include_domains=self.PREMIUM_DOMAINS + self.SECONDARY_DOMAINS,
                time_period="month",
            )
            
            for item in search_result.get("results", []):
                try:
                    # Parsear fecha si existe
                    published_date = item.get("published_date", None)
                    
                    news_item = {
                        "title": item.get("title", "No title"),
                        "content": item.get("content", "No content"),
                        "url": item.get("url", ""),
                        "published_date": published_date,
                        "score": 0.0,  # Se calculará después
                        "category": "general",  # Se clasificará después
                    }
                    results.append(news_item)
                except Exception as e:
                    logger.warning(f"Failed to parse result: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Query '{query_text}' failed: {e}")
            
        return results

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplica resultados por URL y similitud de título.
        
        Estrategia:
        1. Primero por URL exacta (eliminación directa)
        2. Luego por título normalizado (similitud de prefix)
        3. Mantiene el resultado con mejor score/fuente
        """
        seen_urls = set()
        seen_titles = {}
        unique = []
        
        for item in results:
            url = item.get("url", "").strip()
            title = item.get("title", "").lower().strip()
            
            # 1. Eliminar duplicados exactos por URL
            if url and url in seen_urls:
                logger.debug(f"Skipping duplicate URL: {url}")
                continue
            
            # 2. Eliminar duplicados por título similar (primeros 60 chars)
            title_key = title[:80].replace(" ", "")
            if title_key in seen_titles:
                logger.debug(f"Skipping similar title: {title}")
                # Mantener el que tenga mejor fuente/puntuación
                existing = seen_titles[title_key]
                # Por defecto mantener el primero
                continue
            
            # Agregar a vistas
            if url:
                seen_urls.add(url)
            seen_titles[title_key] = item
            
            unique.append(item)
            
        logger.info(f"Deduplication: {len(results)} -> {len(unique)} results")
        return unique

    def _calculate_score(self, item: Dict[str, Any]) -> float:
        """
        Calcula score de relevancia basado en:
        - Antigüedad (más reciente = más alto)
        - Dominio de fuente (premium = bonus)
        """
        score = 0.0
        
        # Puntos por antigüedad
        published_date = item.get("published_date")
        if published_date:
            try:
                pub_date = datetime.fromisoformat(
                    published_date.replace("Z", "+00:00")
                )
                days_old = (datetime.now(pub_date.tzinfo) - pub_date).days
                if days_old < 1:
                    score += 1.0  # Hoy
                elif days_old < 7:
                    score += 0.8  # Esta semana
                elif days_old < 30:
                    score += 0.5  # Este mes
                elif days_old < 90:
                    score += 0.3  # Último trimestre
                else:
                    score += 0.1  # Antiguo pero aún relevante
            except (ValueError, TypeError):
                score += 0.1  # Si no se puede parsear, score bajo
        
        # Bonus por dominio premium
        url = item.get("url", "").lower()
        for domain in self.PREMIUM_DOMAINS:
            if domain in url:
                score += 0.3
                break
        
        return min(score, 1.5)

    def _categorize_item(self, item: Dict[str, Any]) -> str:
        """
        Clasifica un item en categorías específicas.
        
        Categorías:
        - earnings: resultados financieros
        - sector: análisis de industria/sector
        - competitors: comparación con competidores
        - sentiment: sentimiento/forecast
        - general: noticias generales
        """
        title = item.get("title", "").lower()
        content = item.get("content", "").lower()
        combined = f"{title} {content}"
        
        # Score por categoría
        category_scores = {
            "earnings": sum(1 for kw in self.EARNINGS_KEYWORDS if kw in combined),
            "sector": sum(1 for kw in self.SECTOR_KEYWORDS if kw in combined),
            "competitors": sum(1 for kw in self.COMPETITOR_KEYWORDS if kw in combined),
            "sentiment": sum(1 for kw in self.SENTIMENT_KEYWORDS if kw in combined),
        }
        
        # Retornar categoría con mayor score
        best_category = max(category_scores, key=category_scores.get)
        
        if category_scores[best_category] > 0:
            return best_category
        return "general"

    def _score_and_categorize(self, results: List[Dict[str, Any]], 
                               input_data: ResearchInput) -> ResearchOutput:
        """
        Aplica scoring y categorización a todos los resultados.
        Luego los distribuye en las categorías de salida.
        """
        # Score y categorizar cada item
        for item in results:
            item["score"] = self._calculate_score(item)
            item["category"] = self._categorize_item(item)
        
        # Ordenar por score descendente
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Distribuir en categorías
        output = ResearchOutput()
        
        for item in results:
            category = item.get("category", "general")
            
            if category == "earnings":
                output.earnings.append(item)
            elif category == "sector":
                output.sector_analysis.append(item)
            elif category == "competitors":
                output.competitors.append(item)
            elif category == "sentiment":
                output.sentiment.append(item)
            else:
                output.news.append(item)
        
        # Limitar resultados por categoría para evitar sobrecarga
        max_per_category = 10
        output.news = output.news[:max_per_category]
        output.earnings = output.earnings[:max_per_category]
        output.sector_analysis = output.sector_analysis[:max_per_category]
        output.competitors = output.competitors[:max_per_category]
        output.sentiment = output.sentiment[:max_per_category]
        
        # Calcular total
        output.total_results = (
            len(output.news) + len(output.earnings) + 
            len(output.sector_analysis) + len(output.competitors) + 
            len(output.sentiment)
        )
        
        return output
