import logging

from langgraph.graph import StateGraph, END
from src.state import FinancialGraphState
from src.agents.researcher import market_researcher_node
from src.agents.analyst import financial_analyst_node
from src.agents.report_writer import report_writer_node
from src.agents.quality_controller import quality_controller_node

logger = logging.getLogger(__name__)


async def create_financial_graph() -> StateGraph:
    """Construye el grafo de agentes financieros."""

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

    return workflow.compile()
