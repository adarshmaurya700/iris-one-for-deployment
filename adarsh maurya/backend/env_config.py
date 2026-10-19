"""Load .env / .env.local from backend/ and project root without crashing demos."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BACKEND_DIR.parent

if load_dotenv:
    for path in (
        _ROOT_DIR / ".env",
        _ROOT_DIR / ".env.local",
        _BACKEND_DIR / ".env",
        _BACKEND_DIR / ".env.local",
    ):
        load_dotenv(path, override=False)


def get_env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()
