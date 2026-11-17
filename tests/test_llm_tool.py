from unittest.mock import MagicMock, patch

from src.tools.llm_tool import LLMTool, LLMCallResult


class TestLLMToolSingleton:

    def test_singleton_returns_same_instance(self):
        """get_instance() returns the same object on repeated calls."""
        LLMTool.reset_instance()
        instance1 = LLMTool.get_instance()
        instance2 = LLMTool.get_instance()
        assert instance1 is instance2

    def test_singleton_different_from_fresh_init(self):
        """Creating via __init__ directly does not affect singleton."""
        LLMTool.reset_instance()
        with patch.object(LLMTool, '_init_openai'):
            direct = LLMTool()
        with patch.object(LLMTool, '_init_openai'):
            singleton = LLMTool.get_instance()
        assert direct is not singleton

    def test_reset_instance_clears_singleton(self):
        """reset_instance() clears the cached singleton."""
        LLMTool.reset_instance()
        with patch.object(LLMTool, '_init_openai'):
            instance1 = LLMTool.get_instance()
        LLMTool.reset_instance()
        assert LLMTool._instance is None
        with patch.object(LLMTool, '_init_openai'):
            instance2 = LLMTool.get_instance()
        assert instance1 is not instance2

    def test_get_instance_uses_first_parameters(self):
        """Parameters passed to first get_instance call are used; later args ignored."""
        LLMTool.reset_instance()
        with patch.object(LLMTool, '_init_openai') as mock_init:
            inst = LLMTool.get_instance(temperature=0.9, max_retries=5)
        # Verify the instance was created (init was called)
        assert mock_init.called
        assert inst is LLMTool.get_instance()

    def test_llm_call_result_model(self):
        """LLMCallResult Pydantic model serializes correctly."""
        result = LLMCallResult(content="hello", model_used="gpt-4")
        assert result.content == "hello"
        assert result.model_used == "gpt-4"
        d = result.model_dump()
        assert d == {"content": "hello", "model_used": "gpt-4"}


class TestLLMToolCall:

    def test_call_returns_llm_response(self):
        """call() returns the content from the LLM backend."""
        with patch.object(LLMTool, '_init_openai'):
            tool = LLMTool.get_instance()
        tool.llm = MagicMock()
        tool.llm.invoke.return_value.content = "test response"
        tool._backend = "openai"

        result = tool.call("test prompt")
        assert result == "test response"
        tool.llm.invoke.assert_called_once()

    def test_call_uses_cache(self):
        """call() returns cached value when cache_key matches."""
        with patch.object(LLMTool, '_init_openai'):
            tool = LLMTool.get_instance()
        tool.llm = MagicMock()
        tool.llm.invoke.return_value.content = "cached value"
        tool._backend = "openai"

        r1 = tool.call("prompt", cache_key="key1")
        r2 = tool.call("different prompt", cache_key="key1")
        assert r1 == r2 == "cached value"
        tool.llm.invoke.assert_called_once()

    def test_call_with_system_prompt(self):
        """call_with_system_prompt combines system and user prompts for openai."""
        with patch.object(LLMTool, '_init_openai'):
            tool = LLMTool.get_instance()
        tool.llm = MagicMock()
        tool.llm.invoke.return_value.content = "system response"
        tool._backend = "openai"

        result = tool.call_with_system_prompt(
            system_prompt="You are a helper.",
            user_prompt="Hello.",
        )
        assert result == "system response"

    def test_call_with_retry_on_failure(self):
        """call() retries on failure and returns error string after max_retries."""
        with patch.object(LLMTool, '_init_openai'):
            tool = LLMTool(max_retries=2)
        tool.llm = MagicMock()
        tool.llm.invoke.side_effect = Exception("API error")
        tool._backend = "openai"

        result = tool.call("fail prompt")
        assert result.startswith("[ERROR]")
        assert tool.llm.invoke.call_count == 2

    def test_clear_cache(self):
        """clear_cache() empties the internal cache."""
        with patch.object(LLMTool, '_init_openai'):
            tool = LLMTool.get_instance()
        tool._cache = {"a": "1", "b": "2"}
        tool.clear_cache()
        assert tool._cache == {}
