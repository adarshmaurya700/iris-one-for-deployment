"""Load .env / .env.local from backend/ and the project root."""

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BACKEND_DIR.parent

for candidate in (
    _BACKEND_DIR / ".env",
    _BACKEND_DIR / ".env.local",
    _ROOT_DIR / ".env",
    _ROOT_DIR / ".env.local",
):
    if candidate.exists():
        load_dotenv(candidate, override=False)
