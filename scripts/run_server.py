"""Container entrypoint; accepts the hosting provider's PORT."""
import os
from pathlib import Path
import sys

from streamlit.web import cli

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8501"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    sys.argv = ["streamlit", "run", str(Path(__file__).resolve().parents[1] / "app.py"),
                "--server.address=0.0.0.0", f"--server.port={port}", "--server.headless=true"]
    raise SystemExit(cli.main())

