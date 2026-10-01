"""Shared test fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# The Home Assistant test harness blocks sockets globally. On Windows, asyncio
# creates its event loop self-pipe with an AF_INET socketpair, which the blocker
# rejects (it only permits AF_UNIX). Relax the blocker on Windows only; Linux CI
# keeps the protection.
if sys.platform == "win32":
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None


@pytest.fixture
def aircraft_payload() -> dict:
    """Return a sample tar1090 aircraft.json payload."""
    return json.loads((FIXTURES / "aircraft.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
