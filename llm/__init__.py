"""LLM package for LLM Service."""

from llm.deepseek_client import get_deepseek_client, DeepSeekClient

__all__ = ['get_deepseek_client', 'DeepSeekClient']

# Backward-compatible alias: deepseek_client is now a lazy getter
def __getattr__(name):
    if name == 'deepseek_client':
        return get_deepseek_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")