"""Loads config.yaml, the single source of settings for every TokenGate script."""

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config() -> dict:
    """Read config.yaml and return it as a dict."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)
