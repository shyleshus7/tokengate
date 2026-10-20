"""Mock tools for the DevOps Triage Agent. Each returns a LARGE JSON payload from data/."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(filename: str):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def get_recent_logs() -> list:
    """Fetch the most recent application log entries (about 100) across all services."""
    return _load("logs.json")


def list_github_issues() -> list:
    """List open and closed GitHub issues (about 50) for the engineering repo."""
    return _load("issues.json")


def search_runbooks(query: str) -> dict:
    """Search internal runbooks and docs. Returns about 60 ranked results.

    Args:
        query: What to search for, e.g. "database timeout".
    """
    return _load("search_results.json")
