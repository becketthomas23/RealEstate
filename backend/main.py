"""Vercel Services entrypoint for the FastAPI application."""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from backend.api.main import app

