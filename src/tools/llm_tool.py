import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMCallResult(BaseModel):
    """Resultado estandarizado de una llamada LLM."""
    content: str = Field(description="Respuesta generada por el LLM")
    model_used: str = Field(description="Modelo de LLM utilizado")


class LLMTool:
    """
    Herramienta centralizada para llamadas LLM con retry, logging y caching.
    Soporta backend OpenAI o local (llama-cpp-python).

    Singleton: el modelo se carga una sola vez y se comparte entre todas las llamadas.
    """

    _instance: Optional["LLMTool"] = None
    _initialized: bool = False

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 3,
        local_model_path: Optional[str] = None,
        local_enabled: bool = False,
    ):
        # Allow re-init only if _initialized is False (first call) or explicit reset
        if LLMTool._initialized and LLMTool._instance is self:
            return

        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_retries = max_retries
        self._cache: dict[str, str] = {}

        self._use_local = local_enabled or os.getenv("LOCAL_LLM_ENABLED", "false").lower() == "true"
        self._local_model_path = local_model_path or os.getenv("LOCAL_LLM_MODEL", "")

        if self._use_local and self._local_model_path:
            self._init_local()
        else:
            self._init_openai()

        LLMTool._initialized = True
        logger.info(f"LLMTool initialized with backend: {'local' if self._use_local else 'openai'}, model: {self.model_name}")

    @classmethod
    def get_instance(
        cls,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 3,
        local_model_path: Optional[str] = None,
        local_enabled: bool = False,
    ) -> "LLMTool":
        """
        Returns the singleton LLMTool instance. Creates it on first call.
        Parameters are only used on the first invocation; subsequent calls
        return the already-initialized instance regardless of passed arguments.
        """
        if cls._instance is None:
            cls._instance = cls(
                model_name=model_name,
                api_key=api_key,
                temperature=temperature,
                max_retries=max_retries,
                local_model_path=local_model_path,
                local_enabled=local_enabled,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None
        cls._initialized = False

    def _init_openai(self):
        """Inicializa backend OpenAI."""
        from langchain_openai import ChatOpenAI

        self._backend = "openai"
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            temperature=self.temperature,
            max_retries=self.max_retries,
            streaming=False,
        )

    def _init_local(self):
        """Inicializa backend llama-cpp-python."""
        from llama_cpp import Llama

        self._backend = "local"
        n_gpu_layers = -1
        n_ctx = int(os.getenv("LLAMA_N_CTX", "32768"))
        n_threads = int(os.getenv("LLAMA_N_THREADS", "12"))

        logger.info(f"Loading local model: {self._local_model_path}")
        self.llm = Llama(
            model_path=self._local_model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=min(n_ctx, 512),
            verbose=False,
        )
        self.model_name = os.path.basename(self._local_model_path)

    def call(self, prompt: str, cache_key: Optional[str] = None) -> str:
        """
        Ejecuta una llamada LLM con retry y caching opcional.
        """
        if cache_key and cache_key in self._cache:
            logger.debug(f"Cache hit for key: {cache_key}")
            return self._cache[cache_key]

        result = self._execute_with_retry(prompt)

        if cache_key:
            self._cache[cache_key] = result
            logger.debug(f"Cache stored for key: {cache_key}")

        return result

    def _execute_with_retry(self, prompt: str) -> str:
        """Ejecuta la llamada LLM con retry exponencial."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self._backend == "local":
                    content = self._call_local(prompt)
                else:
                    content = self._call_openai(prompt)

                content = content.strip()
                logger.info(f"LLM call successful (attempt {attempt}, model: {self.model_name})")
                return content

            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(
                    f"LLM call failed (attempt {attempt}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                import time
                time.sleep(wait_time)

        logger.error(f"LLM call failed after {self.max_retries} attempts: {last_error}")
        return f"[ERROR] LLM generation failed after {self.max_retries} attempts: {last_error}"

    def _call_openai(self, prompt: str) -> str:
        """Llama a OpenAI API."""
        response = self.llm.invoke(prompt)
        return response.content

    def _call_local(self, prompt: str) -> str:
        """Llama al modelo local via llama-cpp-python."""
        result = self.llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=self.temperature,
        )
        return result["choices"][0]["message"]["content"]

    def call_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        cache_key: Optional[str] = None,
    ) -> str:
        """Ejecuta una llamada LLM con system prompt y user prompt separados."""
        if self._backend == "local":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return self._call_local_with_messages(messages)
        else:
            prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
            return self.call(prompt, cache_key=cache_key)

    def _call_local_with_messages(self, messages: list) -> str:
        """Llama al modelo local con lista de mensajes."""
        result = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=4096,
            temperature=self.temperature,
        )
        return result["choices"][0]["message"]["content"]

    def clear_cache(self):
        """Limpia el cache de llamadas LLM."""
        self._cache.clear()
        logger.info("LLM cache cleared")
