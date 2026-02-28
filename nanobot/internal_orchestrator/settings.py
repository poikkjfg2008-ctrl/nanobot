"""Configuration for internal orchestration deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class InternalOrchestratorSettings:
    """Environment-driven settings for intranet deployment."""

    llm_backend: str = "vllm"  # vllm | ollama
    llm_base_url: str = "http://127.0.0.1:8000"
    llm_api_key: str = "sk-internal"
    llm_model: str = "qwen2.5-32b-instruct"
    request_timeout_s: float = 45.0
    max_loop_steps: int = 3
    temperature: float = 0.1

    @classmethod
    def from_env(cls) -> "InternalOrchestratorSettings":
        defaults = cls()
        return cls(
            llm_base_url=os.getenv("INTERNAL_ORCH_LLM_BASE_URL", defaults.llm_base_url),
            llm_backend=os.getenv("INTERNAL_ORCH_LLM_BACKEND", defaults.llm_backend).lower(),
            llm_api_key=os.getenv("INTERNAL_ORCH_LLM_API_KEY", defaults.llm_api_key),
            llm_model=os.getenv("INTERNAL_ORCH_LLM_MODEL", defaults.llm_model),
            request_timeout_s=float(os.getenv("INTERNAL_ORCH_REQUEST_TIMEOUT_S", defaults.request_timeout_s)),
            max_loop_steps=int(os.getenv("INTERNAL_ORCH_MAX_LOOP_STEPS", defaults.max_loop_steps)),
            temperature=float(os.getenv("INTERNAL_ORCH_TEMPERATURE", defaults.temperature)),
        )
