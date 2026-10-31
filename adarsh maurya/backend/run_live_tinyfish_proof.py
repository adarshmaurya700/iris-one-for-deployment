"""Compatibility entry point for the bounded, redacted integration diagnostic."""
from pathlib import Path
import runpy
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/check_integrations.py'), run_name='__main__')
