"""Aviation phonetic pronunciation helpers.

TTS engines read identifiers like ``N704CT`` or ``DAL100`` as words, which is hard
to understand. This converts them into ICAO/NATO phonetics (letters spelled out,
digits spoken individually, ``9`` as "niner") before they are spoken.
"""

from __future__ import annotations

import re

# ICAO/NATO phonetic alphabet, using spellings that read well in TTS.
_NATO: dict[str, str] = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu",
}

_DIGITS: dict[str, str] = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "niner",
}

_SPELLABLE = re.compile(r"[A-Za-z0-9]")
_LETTERS_DIGITS = re.compile(r"^([A-Za-z]+)(\d+)$")


def spell(text: str | None) -> str:
    """Spell letters phonetically and digits individually."""
    if not text:
        return text or ""
    words = [_token(ch) for ch in text if _SPELLABLE.match(ch)]
    return " ".join(word for word in words if word)


def _token(char: str) -> str | None:
    upper = char.upper()
    if upper in _NATO:
        return _NATO[upper]
    return _DIGITS.get(char)


def spoken_registration(registration: str | None) -> str | None:
    """Return a spoken form of a registration, or None if empty."""
    if not registration:
        return None
    return spell(registration)


def spoken_callsign(
    callsign: str | None, airline: str | None, style: str
) -> str | None:
    """Return a spoken form of a callsign.

    With the ``airline`` style, a ``<letters><digits>`` callsign and a known
    airline become ``"<airline> <digits>"``; otherwise (or with the ``phonetic``
    style) the characters are spelled out.
    """
    if not callsign:
        return None
    if style == "airline" and airline:
        match = _LETTERS_DIGITS.match(callsign)
        if match:
            return f"{airline} {spell(match.group(2))}"
    return spell(callsign)
