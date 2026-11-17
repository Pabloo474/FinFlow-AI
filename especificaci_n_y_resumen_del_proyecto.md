# Documento de Arquitectura y Especificación del Proyecto (SDD)
## Sistema Multi-Agente de Análisis Financiero y Generación de Reportes

---

## 1. Visión General del Proyecto

Este proyecto consiste en el desarrollo de una solución empresarial autónoma basada en **sistemas multi-agente** utilizando **LangGraph** y la filosofía de desarrollo **Specification-Driven Development (SDD)**.

El sistema recibe un indicador bursátil (*ticker*) y un objetivo de análisis, coordina una red de agentes especializados (investigación, análisis cuantitativo, redacción y auditoría), y produce un informe ejecutivo detallado, preciso y validado.

---

## 2. Filosofía de Desarrollo: SDD (Specification-Driven Development)

Para garantizar la fiabilidad y escalabilidad en entornos de producción:

1. **Contratos Estrictos (Pydantic):** Ningún agente intercambia texto no estructurado o diccionarios libres; todo flujo inter-nodo se valida mediante modelos con tipos definidos.
2. **Determinismo y Observabilidad:** Monitoreo y trazabilidad paso a paso (*tracing*) de los razonamientos de los agentes.
3. **Control de Calidad Integrado (Quality Gate):** Inclusión de bucles de retroalimentación donde un agente auditor convalida el resultado antes de la entrega final.

---

## 3. Arquitectura del Sistema (LangGraph)

El sistema opera sobre un **grafo de estado** que gestiona la ejecución distribuida de tareas.

```
                  [Inicio: Ticker + Objetivo]
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Market Researcher  │ (Noticias y Macro)
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Financial Analyst  │ (Métricas RAG / Datos)
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Report Writer    │ (Redacción del Borrador)
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Quality Controller  │ (Auditoría de Datos)
                    └──────────┬──────────┘
                               │
            ┌──────────────────┴──────────────────┐
 (Feedback / Iteraciones < 3)             (Aprobado / Límite)
            │                                     │
            ▼                                     ▼
 [Re-envío a Report Writer]                [Generación PDF / FIN]
```

---

## 4. Estructura de Nodos y Agentes

| Nodo | Rol | Herramientas / Funcionalidad | Entradas/Salidas Clave |
| :--- | :--- | :--- | :--- |
| **`market_researcher`** | Investigador de Mercado | Tavily / Google Search API. Extrae tendencias macroeconómicas y noticias recientes. | E: Ticker<br>S: `raw_news` |
| **`financial_analyst`** | Analista Cuantitativo | RAG sobre PDFs corporativos (10-K), APIs financieras. Calcula ratios contables clave. | E: Ticker, News<br>S: `financial_metrics` |
| **`report_writer`** | Redactor Ejecutivo | Síntesis y redacción. Ensambla el borrador en formato estructurado (Markdown/PDF). | E: Metrics, News<br>S: `analysis_draft` |
| **`quality_controller`**| Auditor de Calidad | Verificación de coherencia lógica y numérica. Identifica alucinaciones o errores. | E: Draft, Metrics<br>S: `qa_feedback`, `iteration_count` |

---

## 5. Especificación del Estado Compartido (`State Schema`)

Definición de la estructura de datos compartida por el grafo (`FinancialGraphState`):

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

---

## 6. Estructura del Proyecto en Disco

```text
financial-multiagent-sdd/
├── docs/specs/                     # Documentación SDD y Especificaciones
│   ├── 01-architecture.md     # Flujos del grafo y descripción de agentes
│   ├── 02-state-schema.md     # Contratos de datos (Pydantic / TypedDict)
│   └── 03-evaluation-plan.md  # Criterios de prueba y validación
├── src/                       # Código Fuente
│   ├── agents/                # Módulos de los nodos (researcher, analyst, etc.)
│   ├── state.py               # Definición del estado y esquemas
│   ├── tools/                 # Conectores RAG, APIs financieras y buscadores
│   └── graph.py               # Ensamblaje y compilación de LangGraph
├── tests/                     # Pruebas unitarias e integración (Pytest)
├── .env                       # Variables de entorno y llaves API
└── README.md                  # Guía de instalación y ejecución
```

---

## 7. Próximos Pasos de Implementación

1. Configuración de entorno y dependencias (`langgraph`, `pydantic`, `langchain-openai`).
2. Implementación del módulo de estado (`src/state.py`).
3. Construcción de herramientas personalizadas (búsqueda e integración de RAG).
4. Desarrollo de nodos y ensamblaje del grafo con control de calidad iterativo.