"""Provider registry for intranet-only deployments.

This build intentionally supports only two local inference backends:
- Ollama
- vLLM (or other OpenAI-compatible local gateways)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    """One LLM provider's metadata."""

    name: str
    keywords: tuple[str, ...]
    env_key: str
    display_name: str = ""

    litellm_prefix: str = ""
    skip_prefixes: tuple[str, ...] = ()
    env_extras: tuple[tuple[str, str], ...] = ()

    is_gateway: bool = False
    is_local: bool = False
    detect_by_key_prefix: str = ""
    detect_by_base_keyword: str = ""
    default_api_base: str = ""

    strip_model_prefix: bool = False
    model_overrides: tuple[tuple[str, dict[str, Any]], ...] = ()
    is_oauth: bool = False
    is_direct: bool = False
    supports_prompt_caching: bool = False

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="ollama",
        keywords=("ollama",),
        env_key="OLLAMA_API_KEY",
        display_name="Ollama",
        litellm_prefix="ollama",
        skip_prefixes=("ollama/",),
        is_local=True,
        detect_by_base_keyword="11434",
        default_api_base="http://127.0.0.1:11434",
    ),
    ProviderSpec(
        name="vllm",
        keywords=("vllm", "hosted_vllm"),
        env_key="HOSTED_VLLM_API_KEY",
        display_name="vLLM/Local",
        litellm_prefix="hosted_vllm",
        skip_prefixes=("hosted_vllm/", "vllm/"),
        is_local=True,
    ),
)


def find_by_model(model: str) -> ProviderSpec | None:
    """Match provider by explicit prefix or keyword in model string."""
    model_lower = model.lower()
    model_prefix = model_lower.split("/", 1)[0] if "/" in model_lower else ""

    for spec in PROVIDERS:
        if model_prefix == spec.name:
            return spec
    for spec in PROVIDERS:
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None


def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """Detect local backend by explicit provider name or api_base."""
    del api_key  # retained for API compatibility

    if provider_name:
        spec = find_by_name(provider_name)
        if spec and (spec.is_gateway or spec.is_local):
            return spec

    for spec in PROVIDERS:
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec

    return None


def find_by_name(name: str) -> ProviderSpec | None:
    """Find provider spec by config field name."""
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None
