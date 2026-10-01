"""Tests for aviation phonetic pronunciation."""

from __future__ import annotations

from custom_components.piaware_adsb.phonetics import (
    spell,
    spoken_callsign,
    spoken_registration,
)


def test_spell_registration() -> None:
    assert spell("N704CT") == "November seven zero four Charlie Tango"


def test_spell_hex() -> None:
    assert spell("a53436") == "Alpha five three four three six"


def test_spell_uses_niner() -> None:
    assert spell("N930VT") == "November niner three zero Victor Tango"


def test_spell_empty() -> None:
    assert spell("") == ""
    assert spell(None) == ""


def test_spoken_registration() -> None:
    assert spoken_registration("N123NW") == "November one two three November Whiskey"
    assert spoken_registration(None) is None


def test_spoken_callsign_airline_style() -> None:
    assert (
        spoken_callsign("DAL100", "Delta Air Lines", "airline")
        == "Delta Air Lines one zero zero"
    )


def test_spoken_callsign_airline_falls_back_to_spelling() -> None:
    assert (
        spoken_callsign("DAL100", None, "airline")
        == "Delta Alpha Lima one zero zero"
    )


def test_spoken_callsign_phonetic_style_ignores_airline() -> None:
    assert (
        spoken_callsign("DAL100", "Delta Air Lines", "phonetic")
        == "Delta Alpha Lima one zero zero"
    )


def test_spoken_callsign_ga_registration_is_spelled() -> None:
    assert (
        spoken_callsign("N704CT", "Some Airline", "airline")
        == "November seven zero four Charlie Tango"
    )


def test_spoken_callsign_empty() -> None:
    assert spoken_callsign(None, "Delta", "airline") is None
