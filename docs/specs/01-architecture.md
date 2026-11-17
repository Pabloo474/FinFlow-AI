# Arquitectura del Sistema

## 1. Visión General del Proyecto

Este proyecto consiste en el desarrollo de una solución empresarial autónoma basada en **sistemas multi-agente** utilizando **LangGraph** y la filosofía de desarrollo **Specification-Driven Development (SDD)**.

El sistema recibe un indicador bursátil (*ticker*) y un objetivo de análisis, coordina una red de agentes especializados (investigación, análisis cuantitativo, redacción y auditoría), y produce un informe ejecutivo detallamente, preciso y validado.

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
