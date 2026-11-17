# Plan de Evaluación y Validación

El éxito del sistema se mide mediante la capacidad del `Quality Controller` para detectar discrepancias y asegurar la veracidad de la información financiera extraída.

## 1. Criterios de Evaluación

| Criterio | Descripción | Método de Verificación |
| :--- | :--- | :--- de control |
| **Exactitud Numérica** | Los ratios calculados deben coincidir con los datos de la fuente (yfinance/RAG). | Comparación automatizada de `financial_metrics` vs `raw_news`. |
| **Coherencia Lógica** | El reporte no debe presentar contradicciones entre secciones. | Análisis de texto por el agente `quality_controller`. |
| **Ausencia de Alucinaciones** | No se deben inventar noticias o datos que no existan en las fuentes originales. | Verificación de citas y referencias cruzadas. |
| **Formato y Estructura** | El PDF debe cumplir con la estructura profesional definida (Portada, Secciones, Pie de página). | Validación de la estructura de salida del `report_writer`. |

## 2. Plan de Pruebas (Testing)

1.  **Pruebas Unitarias:** Validar que cada herramienta (Tavily, yfinance) devuelva el formato esperado.
2.  **Pruebas de Integración:** Ejecutar el grafo completo para un ticker conocido (ej. AAPL) y verificar que el estado final contenga `final_report`.
3.  **Pruebas de Resiliencia:** Simular respuestas erróneas de la API para verificar que el `quality_controller` active el bucle de re-iteración.
4.  **Pruebas de Carga/Stress:** Evaluar el tiempo de respuesta y el manejo de tokens en reportes extensos.

## 3. Métricas de Éxito

- **Tasa de Aprobación en Primera Pasada:** Porcentaje de reportes que no requieren iteración.
- **Tasa de Error de Auditoría:** Número de errores detectados por el `quality_controller` que pasan al usuario final (objetivo: 0%).
