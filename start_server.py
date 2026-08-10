import sys
import os
import uvicorn
from main import app

# Add tests/ to sys.path so mock_llm can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
