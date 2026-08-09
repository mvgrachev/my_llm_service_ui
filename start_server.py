import mock_llm  # noqa: F401 — registers llm mock in sys.modules before any project imports
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
