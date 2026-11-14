"""
 * author Antonio Sirignano
 * created on 19-08-2026-07h-45m
 * github: https://github.com/antsiri
 * copyright 2026

Minimal FastAPI server under test.

Serves the sample binary files under ``/samples`` and exposes a ``/health``
endpoint used by the orchestrator to check that the server is up.
Run with: ``uvicorn server.app:app``.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Folder containing the generated sample files (see generate_samples.py)
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Workload Characterization Server")

# Static file serving: GET /samples/<filename>
app.mount("/samples", StaticFiles(directory=STATIC_DIR), name="samples")


@app.get("/health")
def health():
    """Health-check endpoint: always returns ``{"status": "ok"}``."""
    return {"status": "ok"}
