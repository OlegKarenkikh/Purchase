import os
from typing import List, Dict, Any, Optional

import httpx


class OpenAILikeClient:
    """Клиент для OpenAI-совместимого API (включая vLLM).

    Ожидается совместимость с /v1/chat/completions.
    Базовые параметры берутся из окружения:
      - OPENAI_BASE_URL (например, http://localhost:8000/v1)
      - OPENAI_API_KEY (если требуется авторизация)
      - OPENAI_MODEL (имя модели по умолчанию)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "local-vllm-model")
        self.timeout = timeout

        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        presence_penalty: float = 0.6,
        frequency_penalty: float = 0.8,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Вызов /chat/completions и возврат текста ответа модели."""

        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
        }

        if response_format is not None:
            # Например: {"type": "json_object"} для строгого JSON-вывода
            payload["response_format"] = response_format

        resp = self._client.post("/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
