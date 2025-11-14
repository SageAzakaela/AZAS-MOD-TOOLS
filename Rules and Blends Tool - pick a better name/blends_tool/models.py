"""Core data definitions for blends editing."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class BlendEntry:
    layer: str
    main_tile: str
    blend_tile: str
    direction: str
    exclude: List[str] = field(default_factory=list)
    extras: Dict[str, str] = field(default_factory=dict)

    @property
    def display_label(self) -> str:
        return f"{self.main_tile} → {self.blend_tile} ({self.direction})"

    def fuzzy_key(self) -> str:
        return (self.main_tile or "").lower()
