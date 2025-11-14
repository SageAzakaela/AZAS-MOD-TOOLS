"""Blends file parser/writer and optimization helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .models import BlendEntry


class BlendRepository:
    """Loads and saves the `Blends.txt` file along with helper operations."""

    def __init__(self, source: Path) -> None:
        self.source = source
        self.version: int = 1
        self.entries: List[BlendEntry] = []

    def load(self) -> None:
        text = self.source.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.entries = []
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("version"):
                _, value = line.split("=", 1)
                self.version = int(value.strip())
                idx += 1
                continue
            if line.startswith("blend"):
                block, idx = self._parse_block(lines, idx + 1)
                if block:
                    self.entries.append(self._entry_from_block(block))
                continue
            idx += 1

    def save(self) -> None:
        serialized = [f"version = {self.version}", ""]
        for entry in self.entries:
            serialized.append("blend")
            serialized.append("{")
            serialized.append(f"    layer = {entry.layer}")
            serialized.append(f"    mainTile = {entry.main_tile}")
            serialized.append(f"    blendTile = {entry.blend_tile}")
            serialized.append(f"    dir = {entry.direction}")
            if entry.exclude:
                serialized.append("    exclude = [")
                for value in entry.exclude:
                    serialized.append(f"        {value}")
                serialized.append("    ]")
            for key, value in entry.extras.items():
                serialized.append(f"    {key} = {value}")
            serialized.append("}")
            serialized.append("")
        self.source.write_text("\n".join(serialized).rstrip() + "\n", encoding="utf-8")

    def optimize_exclusions(self, target: BlendEntry) -> None:
        timings = {entry.main_tile for entry in self.entries if entry is not target}
        target.exclude = sorted(timings)

    def optimize_exclusions_from_priority(self) -> None:
        seen: List[str] = []
        for entry in self.entries:
            unique: List[str] = []
            for tile in seen:
                if tile and tile not in unique:
                    unique.append(tile)
            if "water" in unique:
                unique.remove("water")
                unique.append("water")
            entry.exclude = unique
            seen.append(entry.main_tile)

    def _parse_block(self, lines: List[str], start_index: int) -> Tuple[Dict[str, str | List[str]], int]:
        block: Dict[str, str | List[str]] = {}
        idx = start_index
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("}"):
                return block, idx + 1
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.startswith("["):
                    items, idx = self._collect_list(value, lines, idx)
                    block[key] = items
                    continue
                block[key] = self._normalize(value)
            idx += 1
        return block, idx

    def _collect_list(self, first: str, lines: List[str], index: int) -> Tuple[List[str], int]:
        content = first[first.index("[") + 1 :].strip()
        values: List[str] = []
        if content.endswith("]"):
            stripped = content[:-1].strip()
            if stripped:
                values.append(self._normalize(stripped))
            return values, index + 1
        if content:
            values.append(self._normalize(content))
        idx = index + 1
        while idx < len(lines):
            segment = lines[idx].strip()
            if segment.endswith("]"):
                candidate = segment[:-1].strip()
                if candidate:
                    values.append(self._normalize(candidate))
                return values, idx + 1
            if segment:
                values.append(self._normalize(segment))
            idx += 1
        return values, idx

    @staticmethod
    def _split_items(text: str) -> List[str]:
        return [item.strip().strip(",") for item in text.split() if item.strip()]

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().strip('"')

    @staticmethod
    def _entry_from_block(block: Dict[str, str | List[str]]) -> BlendEntry:
        return BlendEntry(
            layer=str(block.get("layer", "")),
            main_tile=str(block.get("mainTile", "")),
            blend_tile=str(block.get("blendTile", "")),
            direction=str(block.get("dir", "")),
            exclude=BlendRepository._normalize_exclude(block.get("exclude", [])),
            extras={
                key: str(val)
                for key, val in block.items()
                if key
                not in {"layer", "mainTile", "blendTile", "dir", "exclude"}
            },
        )

    @staticmethod
    def _normalize_exclude(value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return [BlendRepository._normalize(item) for item in value]
        if isinstance(value, str):
            return [BlendRepository._normalize(item) for item in value.split() if item]
        return []
