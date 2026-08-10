"""Replace the real LLM client with a mock before any real imports.

Import this module **before** importing main / api / services / llm.
It registers a MagicMock as ``llm.deepseek_client`` in sys.modules so that
all subsequent imports (llm.__init__, services.chat, etc.) bind to the mock
instead of calling a real API.
"""

import sys
from unittest.mock import MagicMock

# Create the mock LLM client
_mock_client = MagicMock()
_mock_client.generate.return_value = (
    '{"products": ["test"], "steps": ["step1"]}'
)

# Ensure the llm package namespace contains the mock
# This must happen before llm/__init__.py runs (i.e. before anyone does
# ``import llm`` or ``from llm import get_deepseek_client``).
if "llm" not in sys.modules:
    import types
    llm_pkg = types.ModuleType("llm")
    llm_pkg.deepseek_client = _mock_client
    llm_pkg.get_deepseek_client = lambda: _mock_client
    sys.modules["llm"] = llm_pkg
else:
    # If llm was already imported but not yet its __init__ (e.g. partial),
    # still inject the mock so downstream reads see it.
    sys.modules["llm"].deepseek_client = _mock_client
    sys.modules["llm"].get_deepseek_client = lambda: _mock_client
