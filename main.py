import asyncio
import logging
import os
import sys
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.graph import create_financial_graph

logger = logging.getLogger("finflow_main")

# Global reference to the aiosqlite connection for cleanup
_checkpointer_conn = None


def setup_logging(log_dir: str = "./logs") -> None:
    """Configura logging centralizado con archivo y consola."""
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"app_{timestamp}.log")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")


async def run_analysis(ticker: str, objective: str = None) -> dict:
    """Ejecuta el análisis y formatea la salida."""
    global _checkpointer_conn

    graph = await create_financial_graph()

    initial_state = {
        "company_ticker": ticker.upper(),
        "target_objective": objective or f"Analyze recent performance for {ticker}",
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
    config = {"configurable": {"thread_id": f"analysis_{ticker}"}}
    result = await graph.ainvoke(initial_state, config=config)

    return result


async def shutdown() -> None:
    """Cierra gracefulmente las conexiones async antes de que el event loop termine."""
    global _checkpointer_conn

    try:
        if _checkpointer_conn is not None:
            await _checkpointer_conn.close()
            _checkpointer_conn = None
            logger.info("Checkpointer database connection closed")
    except RuntimeError as e:
        # Event loop may already be closed; that's acceptable at shutdown
        if "Event loop is closed" in str(e) or "closed" in str(e).lower():
            logger.debug("Event loop already closed during shutdown (acceptable)")
        else:
            logger.warning(f"Unexpected error during shutdown: {e}")
    except Exception as e:
        logger.warning(f"Error during async cleanup: {e}")


def print_report(result: dict) -> None:
    """Formatea e imprime el reporte final."""
    print("\n" + "=" * 70)
    print("FINANCIAL ANALYSIS REPORT")
    print("=" * 70)
    print(result.get("final_report", "No report generated"))
    print("\n" + "=" * 70)
    print(f"Company: {result.get('company_ticker')}")
    print(f"QA Passed: {result.get('qa_passed')}")
    print(f"Iterations: {result.get('iteration_count')}")
    if result.get("errors"):
        print(f"Errors: {result['errors']}")
    print("=" * 70)


async def main() -> None:
    setup_logging()

    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    objective = sys.argv[2] if len(sys.argv) > 2 else None

    result = await run_analysis(ticker, objective)
    print_report(result)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Run async cleanup to close aiosqlite connections
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(shutdown())
        finally:
            loop.close()
