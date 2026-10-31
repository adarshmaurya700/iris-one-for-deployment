"""Convenient local launcher: python app.py. The application uses FastAPI."""
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'backend'))
from main import app  # noqa: E402, F401
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('PORT', '8000')))
