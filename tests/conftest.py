"""Pytest configuration for LLM Service."""

import os
import sys

# Set up environment variables before any imports
os.environ['YANDEX_CLOUD_FOLDER'] = 'test-folder-id'
os.environ['YANDEX_CLOUD_API_KEY'] = 'test-api-key'
os.environ['YANDEX_CLOUD_MODEL'] = 'deepseek-v4-flash/latest'
os.environ['YANDEX_CLOUD_BASE_URL'] = 'https://ai.api.cloud.yandex.net/v1'
os.environ['APP_ENV'] = 'test'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

# ---------------------------------------------------------------------------
# Mock the real LLM client BEFORE any project module is imported.
#
# services.chat imports ``from llm import get_deepseek_client``.  If the real
# llm package is loaded first, its module-level code will try to connect to
# Yandex Cloud (or at least import openai with real credentials).  By
# inserting a fake ``llm`` module into sys.modules *first*, we guarantee
# that every subsequent import of ``llm`` (or ``llm.get_deepseek_client``)
# receives our mock instead of the real implementation.
#
# This must happen before ``import main`` / ``import api`` / ``import services``.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from mock_llm import _mock_client  # noqa: E402  # registers llm in sys.modules

# Clear any previously cached project imports so they reload with the mock
for module_name in list(sys.modules.keys()):
    if module_name in (
        'llm', 'llm.deepseek_client',
        'services', 'services.chat',
        'api', 'api.routes', 'api.models', 'api.__init__',
        'config', 'config.config', 'config.logging_config', 'config.__init__',
        'cache', 'cache.redis_client', 'cache.__init__',
        'main',
    ):
        del sys.modules[module_name]
