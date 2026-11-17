import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPrintReport:

    def test_print_report_outputs_report(self, capsys):
        """print_report() prints the final report and metadata."""
        from main import print_report
        result = {
            "final_report": "This is the report.",
            "company_ticker": "GOOGL",
            "qa_passed": True,
            "iteration_count": 2,
            "errors": [],
        }
        print_report(result)
        captured = capsys.readouterr()
        assert "FINANCIAL ANALYSIS REPORT" in captured.out
        assert "This is the report." in captured.out
        assert "GOOGL" in captured.out
        assert "True" in captured.out
        assert "2" in captured.out

    def test_print_report_no_errors(self, capsys):
        """print_report() omits errors section when empty."""
        from main import print_report
        result = {
            "final_report": "clean report",
            "company_ticker": "MSFT",
            "qa_passed": True,
            "iteration_count": 0,
            "errors": [],
        }
        print_report(result)
        captured = capsys.readouterr()
        assert "Errors:" not in captured.out

    def test_print_report_with_errors(self, capsys):
        """print_report() includes errors when present."""
        from main import print_report
        result = {
            "final_report": "partial report",
            "company_ticker": "TSLA",
            "qa_passed": False,
            "iteration_count": 3,
            "errors": ["Network timeout", "Rate limited"],
        }
        print_report(result)
        captured = capsys.readouterr()
        assert "Network timeout" in captured.out
        assert "Rate limited" in captured.out

    def test_print_report_no_report(self, capsys):
        """print_report() shows fallback when no report."""
        from main import print_report
        result = {
            "final_report": None,
            "company_ticker": "NOOP",
            "qa_passed": False,
            "iteration_count": 0,
            "errors": ["None"],
        }
        print_report(result)
        captured = capsys.readouterr()
        assert "No report generated" in captured.out


class TestRunAnalysis:

    @patch("main.create_financial_graph")
    async def test_run_analysis_returns_result(self, mock_graph):
        """run_analysis() returns the graph result dict."""
        from main import run_analysis
        mock_graph.return_value = AsyncMock()
        mock_graph.return_value.ainvoke = AsyncMock(return_value={"final_report": "ok"})

        result = await run_analysis("AAPL")
        assert result == {"final_report": "ok"}
        mock_graph.return_value.ainvoke.assert_called_once()

    @patch("main.create_financial_graph")
    async def test_run_analysis_uses_ticker(self, mock_graph):
        """run_analysis() uppercases the ticker in initial state."""
        from main import run_analysis
        mock_graph.return_value = AsyncMock()
        mock_graph.return_value.ainvoke = AsyncMock(return_value={})

        await run_analysis("aapl")
        call_args = mock_graph.return_value.ainvoke.call_args
        state = call_args[0][0]
        assert state["company_ticker"] == "AAPL"

    @patch("main.create_financial_graph")
    async def test_run_analysis_with_objective(self, mock_graph):
        """run_analysis() passes custom objective."""
        from main import run_analysis
        mock_graph.return_value = AsyncMock()
        mock_graph.return_value.ainvoke = AsyncMock(return_value={})

        await run_analysis("AAPL", objective="Custom goal")
        call_args = mock_graph.return_value.ainvoke.call_args
        state = call_args[0][0]
        assert state["target_objective"] == "Custom goal"

    @patch("main.create_financial_graph")
    async def test_run_analysis_default_objective(self, mock_graph):
        """run_analysis() generates default objective when none provided."""
        from main import run_analysis
        mock_graph.return_value = AsyncMock()
        mock_graph.return_value.ainvoke = AsyncMock(return_value={})

        await run_analysis("AAPL")
        call_args = mock_graph.return_value.ainvoke.call_args
        state = call_args[0][0]
        assert "AAPL" in state["target_objective"]


class TestShutdown:

    @patch("main._checkpointer_conn", None)
    async def test_shutdown_no_connection(self):
        """shutdown() handles None connection gracefully."""
        from main import shutdown
        await shutdown()

    @patch("main._checkpointer_conn")
    async def test_shutdown_closes_connection(self, mock_conn):
        """shutdown() closes the aiosqlite connection."""
        from main import shutdown
        mock_conn.close = AsyncMock()
        await shutdown()
        mock_conn.close.assert_called_once()
