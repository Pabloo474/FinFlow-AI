# Especificación del Estado Compartido (`State Schema`)

Definición de la estructura de datos compartida por el grafo (`FinancialGraphState`) utilizando Pydcript/TypedDict para asegurar la integridad de los datos entre agentes.

```python
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Contrato Pydantic para Métricas Financieras
class FinancialMetricsModel(BaseModel):
    revenue: float = Field(description="Ingresos totales en USD")
    net_income: float = Field(description="Ingreso neto en USD")
    pe_ratio: Optional[float] = Field(description="Ratio Precio/Beneficio", default=None)
    debt_to_equity: Optional[float] = Field(description="Ratio de endeudamiento", default=None)

# Estado Global del Grafo
class FinancialGraphState(TypedDict):
    company_ticker: str
    target_objective: str
    raw_news: List[Dict[str, Any]]
    financial_metrics: Dict[str, Any]
    analysis_draft: str
    qa_feedback: Optional[str]
    iteration_count: int
    final_report: Optional[str]
```
