"""Helpers shared by palette override UIs."""

from __future__ import annotations

from typing import Iterable, Tuple


def _clamp_byte(value: int) -> int:
    return max(0, min(255, value))


def parse_palette_value(text: str | None) -> tuple[int, int, int] | None:
    if not text:
        return None
    text = text.strip()
    if text.startswith("#"):
        hexstr = text[1:]
        if len(hexstr) == 3:
            hexstr = "".join(ch * 2 for ch in hexstr)
        if len(hexstr) != 6:
            return None
        try:
            r = int(hexstr[0:2], 16)
            g = int(hexstr[2:4], 16)
            b = int(hexstr[4:6], 16)
        except ValueError:
            return None
        return r, g, b

    parts = [part for part in text.replace(",", " ").split() if part]
    if len(parts) < 3:
        return None
    try:
        r = int(parts[0])
        g = int(parts[1])
        b = int(parts[2])
    except ValueError:
        return None
    return _clamp_byte(r), _clamp_byte(g), _clamp_byte(b)


def rgb_to_string(rgb: Iterable[int]) -> str:
    r, g, b = tuple(rgb)
    return f"{r},{g},{b}"


def rgb_to_hex(rgb: Iterable[int]) -> str:
    r, g, b = tuple(rgb)
    return f"#{r:02x}{g:02x}{b:02x}"
