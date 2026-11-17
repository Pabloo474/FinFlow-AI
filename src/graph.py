import asyncio
import logging
import os
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
from src.state import FinancialGraphState
from src.agents.researcher import market_researcher_node
from src.agents.analyst import financial_analyst_node
from src.agents.report_writer import report_writer_node
from src.agents.quality_controller import quality_controller_node

logger = logging.getLogger(__name__)


async def create_financial_graph(checkpoint_dir: str = "./checkpoints") -> StateGraph:
    """
    Construye el grafo de agentes financieros con checkpointing SQLite.
    
    Args:
        checkpoint_dir: Directorio para archivos de checkpoint.
    """
    os.makedirs(checkpoint_dir, exist_ok=True)
        checkpointer_path = os.path.join(checkpoint_dir, "finflow_checkpoints.db")
    conn = await aiosqlite.connect(checkpointer_path)
    checkpointer = AsyncSqliteSaver(conn=conn)

    workflow = StateGraph(FinancialGraphState)

    # Add nodes
    workflow.add_node("market_researcher", market_researcher_node)
    workflow.add_node("financial_analyst", financial_analyst_node)
    workflow.add_node("report_writer", report_writer_node)
    workflow.add_node("quality_controller", quality_controller_node)

    # Define edges
    workflow.set_entry_point("market_researcher")
    workflow.add_edge("market_researcher", "financial_analyst")
    workflow.add_edge("financial_analyst", "report_writer")
    workflow.add_edge("report_writer", "quality_controller")

    # Conditional edge for quality control with max retries
    def route_after_qc(state: FinancialGraphState) -> str:
        if state.get("qa_passed", False) or state.get("iteration_count", 0) >= 3:
            return "end"
        return "retry"

    workflow.add_conditional_edges(
        "quality_controller",
        route_after_qc,
        {
            "end": END,
            "retry": "report_writer"
        }
    )

    return workflow.compile(checkpointer=checkpointer)


async def run_analysis(ticker: str, objective: str = None) -> dict:
    """
    Ejecuta el análisis financiero completo.
    
    Args:
        ticker: Ticker de la acción (ej: "AAPL").
        objective: Objetivo personalizado del análisis.
    """
    if objective is None:
        objective = f"Analyze recent performance and outlook for {ticker}"

    graph = await create_financial_graph()

    initial_state: FinancialGraphState = {
        "company_ticker": ticker.upper(),
        "target_objective": objective,
        "raw_news": [],
        "financial_metrics": {},
        "analysis_draft": "",
        "qa_feedback": [],
        "qa_passed": False,
        "iteration_count": 0,
        "final_report": None,
        "errors": []
    }

    logger.info(f"Starting financial analysis for {ticker.upper()}")
    result = await graph.ainvoke(initial_state)
    logger.info(f"Analysis complete. QA passed: {result.get('qa_passed')}")
    logger.info(f"Final report length: {len(result.get('final_report', ''))} chars")

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )

    import asyncio

    async def main():
        graph = await create_financial_graph()
        initial_state: FinancialGraphState = {
            "company_ticker": "AAPL",
            "target_objective": "Analyze recent performance and investment outlook",
            "raw_news": [],
            "financial_metrics": {},
            "analysis_draft": "",
            "qa_feedback": [],
            "qa_passed": False,
            "iteration_count": 0,
            "final_report": None,
            "errors": []
        }
        result = await graph.ainvoke(initial_state)
        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        print(result.get("final_report", "No report generated"))
        print("\n" + "=" * 60)
        print(f"QA Passed: {result.get('qa_passed')}")
        print(f"Iterations: {result.get('iteration_count')}")
        print(f"Errors: {result.get('errors', [])}")
        print("=" * 60)

    asyncio.run(main())
