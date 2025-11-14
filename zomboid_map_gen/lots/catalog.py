from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class BuildingAsset:
    path: Path
    category: str
    label: str
    width: int
    height: int
    stories: int
    metadata: Mapping[str, str | int]

    @property
    def footprint(self) -> tuple[int, int]:
        return self.width, self.height


def scan_asset_catalog(root: Path, categories: Mapping[str, Mapping]) -> list[BuildingAsset]:
    """
    Walk the asset tree under `root` and collect every `.tbx` file grouped by
    high-level category (residential/commercial/industrial).
    """
    root = root.expanduser().resolve()
    assets: list[BuildingAsset] = []

    for category, cfg in categories.items():
        folder_name = cfg.get("folder") or category
        cat_dir = (root / folder_name).expanduser()
        if not cat_dir.exists():
            continue

        for tbx in cat_dir.rglob("*.tbx"):
            try:
                meta = _read_tbx_metadata(tbx)
            except Exception:
                meta = {}
            width = int(meta.get("width", cfg.get("fallback_width", 24)))
            height = int(meta.get("height", cfg.get("fallback_height", 24)))
            stories = int(meta.get("stories", cfg.get("fallback_stories", 1)))
            assets.append(
                BuildingAsset(
                    path=tbx,
                    category=category,
                    label=tbx.stem,
                    width=width,
                    height=height,
                    stories=stories,
                    metadata=meta,
                )
            )
    return assets


def _read_tbx_metadata(path: Path) -> dict[str, int | str]:
    tree = ET.parse(path)
    root = tree.getroot()
    meta: dict[str, int | str] = {}

    def _pull(keys: Iterable[str], target: str):
        for key in keys:
            if key in root.attrib:
                meta[target] = _coerce_int(root.attrib[key])
                return True
        return False

    width_keys = ("width", "Width", "w", "xCells")
    height_keys = ("height", "Height", "h", "yCells")
    stories_keys = ("stories", "Stories", "floors", "Levels")

    _pull(width_keys, "width")
    _pull(height_keys, "height")
    pulled_stories = _pull(stories_keys, "stories")

    if "width" not in meta or "height" not in meta:
        _read_floor_stats(root, meta)

    if not pulled_stories:
        floors = root.findall(".//floor")
        if floors:
            meta["stories"] = len(floors)

    meta["source"] = path.name
    return meta


def _read_floor_stats(root: ET.Element, meta: dict[str, int | str]) -> None:
    floor_nodes = root.findall(".//floor")
    max_w = meta.get("width", 0) or 0
    max_h = meta.get("height", 0) or 0
    for floor in floor_nodes:
        w = _coerce_int(floor.attrib.get("width") or floor.attrib.get("Width"))
        h = _coerce_int(floor.attrib.get("height") or floor.attrib.get("Height"))
        if w:
            max_w = max(max_w, w)
        if h:
            max_h = max(max_h, h)
    if max_w:
        meta["width"] = max_w
    if max_h:
        meta["height"] = max_h


def _coerce_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
