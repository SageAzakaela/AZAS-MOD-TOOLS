"""Data models shared between the parser, GUI, and preview layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AliasRule:
    name: str
    tiles: List[str]
    extras: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep values consistent when a tile list is reused.
        self.tiles = list(self.tiles)


@dataclass
class BlendRule:
    layer: str
    main_tile: str
    blend_tile: str
    direction: str
    exclude: Optional[str] = ""
    extras: Dict[str, str] = field(default_factory=dict)


@dataclass
class TileEntry:
    name: str
    path: Path
    tileset: str

    def display_label(self) -> str:
        return f"{self.tileset}/{self.name}"
