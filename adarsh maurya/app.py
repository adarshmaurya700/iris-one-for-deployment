"""
IRIS onE — Streamlit Cloud Entrypoint Alias
===========================================
Default entrypoint alias for Streamlit Community Cloud (share.streamlit.io).
Loads and executes `streamlit_app.py`.
"""

from pathlib import Path
import runpy

if __name__ == "__main__" or True:
    app_file = Path(__file__).resolve().parent / "streamlit_app.py"
    runpy.run_path(str(app_file), run_name="__main__")
