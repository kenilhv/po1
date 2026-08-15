"""Shared fixtures for agent tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("USE_LLM", "0")
os.environ.setdefault("GROQ_API_KEY", "")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Fresh SQLite DB per test with seed data."""
    db_path = tmp_path / "test_invoice_os.db"
    monkeypatch.setattr("database.db.DB_PATH", db_path)
    monkeypatch.setenv("USE_LLM", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from database.db import init_db
    from database import seed

    init_db()
    seed.seed()
    yield db_path
