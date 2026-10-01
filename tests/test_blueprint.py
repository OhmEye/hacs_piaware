"""Tests for the bundled overhead-notification blueprint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BLUEPRINT_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "piaware_adsb"
    / "blueprints"
    / "automation"
    / "piaware_adsb"
    / "overhead_notify.yaml"
)


class _InputLoader(yaml.SafeLoader):
    """YAML loader that records ``!input`` references instead of failing."""


def _input_constructor(loader: _InputLoader, node: yaml.Node) -> dict[str, str]:
    return {"__input__": loader.construct_scalar(node)}


_InputLoader.add_constructor("!input", _input_constructor)


def _load() -> dict[str, Any]:
    return yaml.load(BLUEPRINT_PATH.read_text(encoding="utf-8"), Loader=_InputLoader)


def _iter_inputs(node: Any):
    if isinstance(node, dict):
        if set(node) == {"__input__"}:
            yield node["__input__"]
            return
        for value in node.values():
            yield from _iter_inputs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_inputs(item)


def test_all_inputs_are_declared() -> None:
    data = _load()
    declared = set(data["blueprint"]["input"])
    used = set(_iter_inputs(data))
    assert used <= declared, f"undeclared inputs: {used - declared}"


def test_assist_satellite_targeting() -> None:
    data = _load()
    selector = data["blueprint"]["input"]["assist_satellites"]["selector"]["entity"]
    assert selector["multiple"] is True
    assert any(f.get("domain") == "assist_satellite" for f in selector["filter"])


def test_announces_on_satellites() -> None:
    text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert "assist_satellite.announce" in text
    assert "notify_action" in _load()["blueprint"]["input"]
