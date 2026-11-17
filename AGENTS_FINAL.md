# AGENTS_FINAL.md - Proyecto de Análisis Financiero Multi-Agente

## 1. Descripción del Proyecto
Este proyecto implementa un sistema de análisis financiero autónomo basado en una arquitectura de **Sistemas Multi-Agente (MAS)** utilizando **LangGraph**. El objetivo es automatizar la investigación de mercado, el análisis cuantitativo y la generación de informes ejecutivos de alta calidad.

El sistema utiliza la filosofía **Specification-Driven Development (SDD)**, asegurando que cada intercambio de información entre agentes esté regido por contratos estrictos (Pydenta) y que el flujo sea determinista, observable y auditable.

## 2. Arquitectura del Grafo (LangGraph)
El flujo de trabajo es un grafo dirigido que coordina los siguientes nodos:

1.  **`market_researcher`**: Utiliza herramientas de búsqueda (Tavily/Google) para extraer noticias y tendencias macroeconómicas.
2.  **`financial_analyst`**: Procesa datos financieros (simulados/API) para calcular ratios clave como P/E, ingresos y beneficios.
3.  **`report_writer`**: Sintetiza la información recolectada en un informe estructurado en Markdown.
4.  **`quality_controller`**: Actúa como un "Quality Gate". Verifica la consistencia entre los datos financieros y el texto del reporte. Si detecta errores, redirige el flujo de vuelta al `report_writer` para una re-redacción.

## 3. Principios de Diseño Aplicados
- **Contratos de Datos (Pydantic):** Uso de `FinancialGraphState` para garantizar que la estructura de datos sea consistente y validada en cada paso.
- **Resiliencia y Auditoría:** Implementación de un bucle de retroalimentación (feedback loop) que permite hasta 3 iteraciones para corregir alucinaciones o errores numéricos.
- **Modularidad:** Herramientas de búsqueda y análisis están desacopladas de la lógica de los agentes, permitiendo su reemplazo o expansión.

## 4. Rol del LLM en el Desarrollo
Para el correcto desarrollo y mantenimiento de este proyecto, un LLM debe actuar bajo los siguientes principios:

- **Arquitecto de Software Senior:** No solo escribir código, sino asegurar que cada cambio respete los contratos definidos en `src/state.py`.
- **Enfoque en Contratos Primero:** Antes de implementar cualquier lógica, el LLM debe definir o validar los modelos Pydantic involucrados.
- **Mentalidad de Auditoría:** Al escribir agentes, el LLM debe prever los casos de error y las validaciones necesarias para el `quality_controller`.
- **Documentación y Trazabilidad:** Mantener la documentación de requerimientos (`docs/requirements.md`) y los checkpoints (`checkpoints/`) actualizados para garantizar la continuidad del desarrollo.

## 5. Conclusión
El sistema está diseñado para ser escalable y robusto, transformando datos financieros crudos en inteligencia de negocio estructurada y validada, minimizando el riesgo de error humano o alucinaciones de modelos de lenguaje.
