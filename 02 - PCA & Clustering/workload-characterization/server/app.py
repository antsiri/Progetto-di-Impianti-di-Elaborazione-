"""
 * author Antonio Sirignano
 * created on 19-08-2026-07h-45m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Workload Characterization Server")

app.mount("/samples", StaticFiles(directory=STATIC_DIR), name="samples")


@app.get("/health")
def health():
    return {"status": "ok"}