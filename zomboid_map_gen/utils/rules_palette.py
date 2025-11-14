"""Utilities for loading and overriding the Rules.txt color palette."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Dict, Tuple

from ..config import DEFAULT_RULES

LAYER_TO_SECTION: Dict[str, str] = {
    "0_Floor": "terrain",
    "0_Vegetation": "vegetation",
}

_CACHE: Dict[str, Tuple[Dict[str, Dict[str, Tuple[int, int, int]]], str | None]] = {}


def get_rules_file(conf: dict) -> Path | None:
    worlded = conf.get("worlded", {}) or {}
    candidate = worlded.get("rules_file")
    if candidate:
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
    if DEFAULT_RULES.exists():
        return DEFAULT_RULES
    return None


def _parse_rules(text: str, callback: Callable[[str, str, Tuple[int, int, int]], None]) -> None:
    inside = False
    current: dict[str, str | tuple[int, int, int] | None] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not inside:
            if stripped.lower() == "rule":
                inside = True
                current = {"label": None, "color": None, "layer": None}
            continue
        if stripped == "{":
            continue
        if stripped.startswith("label"):
            current["label"] = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("color"):
            parts = re.findall(r"\d+", stripped)
            if len(parts) >= 3:
                current["color"] = (int(parts[0]), int(parts[1]), int(parts[2]))
        elif stripped.startswith("layer"):
            current["layer"] = stripped.split("=", 1)[1].strip()
        elif stripped == "}":
            inside = False
            label = current.get("label")
            color = current.get("color")
            layer = current.get("layer")
            if label and color and layer:
                callback(layer, label, color)
            current = {}


def load_rules_colors(path: Path) -> Tuple[Dict[str, Dict[str, Tuple[int, int, int]]], str | None]:
    key = str(path.resolve())
    if key in _CACHE:
        return _CACHE[key]
    data: Dict[str, Dict[str, Tuple[int, int, int]]] = {"terrain": {}, "vegetation": {}}
    error: str | None = None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        error = f"Failed to read {path}: {exc}"
        _CACHE[key] = (data, error)
        return data, error

    def _collect(layer: str, label: str, color: Tuple[int, int, int]):
        section = LAYER_TO_SECTION.get(layer)
        if not section:
            return
        data[section][label] = color

    _parse_rules(text, _collect)
    _CACHE[key] = (data, error)
    return data, error


def build_palette_replacements(conf: dict) -> Dict[str, Dict[Tuple[int, int, int], Tuple[int, int, int]]]:
    replacements: Dict[str, Dict[Tuple[int, int, int], Tuple[int, int, int]]] = {
        "terrain": {},
        "vegetation": {},
    }
    rules_path = get_rules_file(conf)
    if not rules_path:
        return replacements
    rules, _ = load_rules_colors(rules_path)
    overrides = conf.get("rules_palette", {}) or {}
    for section in ("terrain", "vegetation"):
        section_overrides = overrides.get(section, {}) or {}
        defaults = rules.get(section, {})
        for label, override in section_overrides.items():
            default_color = defaults.get(label)
            if not default_color:
                continue
            values = []
            for c in override[:3]:
                try:
                    values.append(max(0, min(255, int(c))))
                except Exception:
                    values = []
                    break
            if len(values) != 3:
                continue
            replacements[section][tuple(default_color)] = tuple(values)
    return replacements


def recolor_image(image, replacements: Dict[Tuple[int, int, int], Tuple[int, int, int]]):
    if not replacements:
        return image
    img = image.convert("RGBA")
    px = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            current = px[x, y]
            base = current[:3]
            replacement = replacements.get(base)
            if replacement:
                px[x, y] = (*replacement, current[3])
    return img
