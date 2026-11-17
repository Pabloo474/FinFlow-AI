import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def reset_llm_singleton():
    """Reset LLMTool singleton before and after each test."""
    from src.tools.llm_tool import LLMTool
    LLMTool.reset_instance()
    yield
    LLMTool.reset_instance()


@pytest.fixture
def mock_llm_tool():
    """Return a mock LLMTool instance without initializing any real LLM."""
    from src.tools.llm_tool import LLMTool
    LLMTool.reset_instance()

    with patch.object(LLMTool, '_init_openai') as mock_init:
        instance = LLMTool.get_instance()
        mock_init.return_value = None
        instance.llm = MagicMock()
        instance._backend = "openai"
        instance._cache = {}
        yield instance


@pytest.fixture
def sample_result():
    """Return a sample analysis result dict."""
    return {
        "final_report": "Sample financial analysis report for AAPL.",
        "company_ticker": "AAPL",
        "qa_passed": True,
        "iteration_count": 1,
        "errors": [],
        "raw_news": [],
        "financial_metrics": {},
        "analysis_draft": "",
        "qa_feedback": [],
    }
