"""Base settings — shared across all environments."""
import os
from typing import Optional


class BaseSettings:
    """Shared defaults that apply to every environment."""

    def __init__(self, env: str = "development"):
        self.env: str = env
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8000"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_format: str = os.getenv("LOG_FORMAT", "default")
        self.log_file: str = os.getenv("LOG_FILE", "app.log")

        # LLM API Keys
        self.yandex_cloud_api_key: Optional[str] = os.getenv(
            "YANDEX_CLOUD_API_KEY"
        )
        self.yandex_cloud_folder: Optional[str] = os.getenv(
            "YANDEX_CLOUD_FOLDER"
        )
        self.yandex_cloud_model: Optional[str] = os.getenv(
            "YANDEX_CLOUD_MODEL"
        )
        self.yandex_cloud_base_url: Optional[str] = os.getenv(
            "YANDEX_CLOUD_BASE_URL"
        )
        self.system_prompt: Optional[str] = os.getenv("PROMPT")

        # Redis Settings
        self.redis_url: str = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db: int = int(os.getenv("REDIS_DB", "0"))

        # Network check
        self.network_check_timeout: int = int(
            os.getenv("NETWORK_CHECK_TIMEOUT", "5")
        )

        # Streamlit UI
        self.fastapi_url: str = os.getenv(
            "FASTAPI_URL",
            "http://localhost:8000"
        )

        self.fastapi_timeout: int = int(
            os.getenv(
                "FASTAPI_TIMEOUT",
                "60"
            )
        )


class DevSettings(BaseSettings):
    """Development environment overrides."""

    def __init__(self):
        super().__init__(env="development")
        # Verbose logging
        self.log_level = "DEBUG"
        self.log_file = "app.log"
        # LLM
        self.deepseek_temperature: float = 0.7
        self.deepseek_cache_ttl: int = int(
            os.getenv("DEEPSEEK_CACHE_TTL", "600")
        )
        self.deepseek_max_output_tokens: int = 1500
        self.deepseek_timeout: int = 60
        # Redis — local
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class TestSettings(BaseSettings):
    """Test environment overrides."""

    def __init__(self):
        super().__init__(env="test")
        # Quiet logging during tests
        self.log_level = "WARNING"
        self.log_file = "test.log"
        # LLM — fast, deterministic
        self.deepseek_temperature: float = 0.0
        self.deepseek_cache_ttl: int = int(
            os.getenv("DEEPSEEK_CACHE_TTL", "600")
        )
        self.deepseek_max_output_tokens: int = 512
        self.deepseek_timeout: int = 10
        # Redis — local
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class ProdSettings(BaseSettings):
    """Production environment overrides."""

    def __init__(self):
        super().__init__(env="production")
        # Production logging
        self.log_level = "INFO"
        self.log_file = os.getenv("LOG_FILE", "/tmp/app.log")
        # LLM
        self.deepseek_temperature: float = 0.3
        self.deepseek_cache_ttl: int = int(
            os.getenv("DEEPSEEK_CACHE_TTL", "600")
        )
        self.deepseek_max_output_tokens: int = int(
            os.getenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1500")
        )
        self.deepseek_timeout: int = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))
        # Redis — possibly remote
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ENV_MAP = {
    "development": DevSettings,
    "test": TestSettings,
    "production": ProdSettings,
}


def get_settings() -> BaseSettings:
    """Return a Settings instance tuned for the current APP_ENV."""
    env = os.getenv("APP_ENV", "development").strip().lower()
    cls = _ENV_MAP.get(env, DevSettings)
    return cls()
