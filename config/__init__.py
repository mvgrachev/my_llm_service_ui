"""Configuration package for LLM Service."""

from config.config import get_settings


class _SettingsProxy:
    """Thin proxy that forwards every attribute to the env-specific instance."""

    __slots__ = ("_instance", "_internal_names")

    def __getattribute__(self, name: str):
        internal = object.__getattribute__(self, "_internal_names")
        if name in internal:
            return object.__getattribute__(self, name)
        # Lazy-init the env-specific settings once
        instance = object.__getattribute__(self, "_instance")
        if instance is None:
            instance = get_settings()
            object.__setattr__(self, "_instance", instance)
        return getattr(instance, name)

    def __init__(self):
        self._instance = None
        self._internal_names = {"_instance", "_internal_names"}


# Module-level singleton that delegates to the env-specific settings
settings = _SettingsProxy()

__all__ = ["settings"]
