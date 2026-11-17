from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from operator import add

from pydantic import BaseModel, Field


# === Contract Pydantic Models ===


class FinancialMetricsModel(BaseModel):
    """Contrato estricto para métricas financieras validadas."""
    revenue: float = Field(description="Ingresos totales en USD")
    net_income: float = Field(description="Ingreso neto en USD")
    pe_ratio: Optional[float] = Field(default=None, description="Ratio Precio/Beneficio")
    debt_to_equity: Optional[float] = Field(default=None, description="Ratio de endeudamiento")
    ticker: str = Field(default="", description="Ticker de la acción")
    currency: str = Field(default="USD", description="Moneda de las métricas")
    fiscal_year: Optional[int] = Field(default=None, description="Año fiscal de los datos")

    def to_display_dict(self) -> Dict[str, Any]:
        """Convierte métricas a formato legible para el reporte."""
        result = {}
        if self.revenue != 0:
            result["Revenue"] = f"${self.revenue:,.0f}"
        if self.net_income != 0:
            result["Net Income"] = f"${self.net_income:,.0f}"
        if self.pe_ratio is not None:
            result["P/E Ratio"] = f"{self.pe_ratio:.2f}"
        if self.debt_to_equity is not None:
            result["Debt/Equity"] = f"{self.debt_to_equity:.2f}"
        return result


class NewsItemModel(BaseModel):
    """Contrato estricto para cada noticia encontrada."""
    title: str = Field(description="Título de la noticia")
    content: str = Field(description="Contenido o resumen de la noticia")
    url: str = Field(description="URL de origen")
    published_date: Optional[str] = Field(default=None, description="Fecha de publicación")


class QAResult(BaseModel):
    """Resultado del control de calidad."""
    passed: bool = Field(description="Si el reporte pasa la validación")
    feedback: str = Field(description="Feedback detallado para correcciones")
    missing_metrics: List[str] = Field(default_factory=list, description="Métricas faltantes")
    hallucination_risks: List[str] = Field(default_factory=list, description="Posibles alucinaciones detectadas")


# === State Definition with Annotated Reducers ===


class FinancialGraphState(TypedDict, total=False):
    """
    Estado compartido del grafo LangGraph con reducers explícitos.
    - errors: se acumulan con append (lista única persistente)
    - raw_news: se acumulan con append (evita duplicados en retries)
    - qa_feedback: se acumula con append (trace completo de iteraciones)
    - iteration_count: se actualiza con max (solo crece)
    """
    company_ticker: str
    target_objective: str
    raw_news: Annotated[List[Dict[str, Any]], add]
    financial_metrics: Dict[str, Any]
    analysis_draft: str
    qa_feedback: Annotated[List[str], add]
    qa_passed: bool
    iteration_count: int
    final_report: Optional[str]
    errors: Annotated[List[str], add]
