"""Parsing, serializing, and asset discovery for the rules/blends GUI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence

from .models import AliasRule, BlendRule, TileEntry


class RulesBlendsManager:
    """Manages loading and saving the textual data files."""

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        blends_path: Optional[Path] = None,
    ) -> None:
        self.rules_path = Path(rules_path) if rules_path else None
        self.blends_path = Path(blends_path) if blends_path else None
        self.rules_version: str = "1"
        self.aliases: List[AliasRule] = []
        self.blends: List[BlendRule] = []

    def load_rules(self, path: Optional[Path] = None) -> List[AliasRule]:
        source = Path(path or self.rules_path)
        text = source.read_text(encoding="utf-8")
        version, blocks = self._extract_blocks(text, keyword="alias")
        self.rules_version = version or self.rules_version
        self.aliases = [
            AliasRule(
                name=block.get("name", ""),
                tiles=block.get("tiles", []),
                extras={
                    key: value
                    for key, value in block.items()
                    if key not in {"name", "tiles"}
                },
            )
            for block in blocks
        ]
        self.rules_path = source
        return self.aliases

    def load_blends(self, path: Optional[Path] = None) -> List[BlendRule]:
        source = Path(path or self.blends_path)
        text = source.read_text(encoding="utf-8")
        _, blocks = self._extract_blocks(text, keyword="blend")
        self.blends = [
            BlendRule(
                layer=block.get("layer", ""),
                main_tile=block.get("mainTile", ""),
                blend_tile=block.get("blendTile", ""),
                direction=block.get("dir", ""),
                exclude=block.get("exclude", ""),
                extras={
                    key: value
                    for key, value in block.items()
                    if key
                    not in {"layer", "mainTile", "blendTile", "dir", "exclude"}
                },
            )
            for block in blocks
        ]
        self.blends_path = source
        return self.blends

    def save_rules(self, path: Optional[Path] = None) -> None:
        target = Path(path or self.rules_path)
        target.write_text(self.serialize_rules(), encoding="utf-8")

    def save_blends(self, path: Optional[Path] = None) -> None:
        target = Path(path or self.blends_path)
        target.write_text(self.serialize_blends(), encoding="utf-8")

    def serialize_rules(self) -> str:
        lines: List[str] = [f"version = {self.rules_version}", ""]
        for alias in self.aliases:
            lines.append("alias")
            lines.append("{")
            lines.append(f"    name = {alias.name}")
            for key, value in alias.extras.items():
                lines.append(f"    {key} = {value}")
            lines.append("    tiles = [")
            for tile in alias.tiles:
                lines.append(f"        {tile}")
            lines.append("    ]")
            lines.append("}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def serialize_blends(self) -> str:
        lines: List[str] = []
        for blend in self.blends:
            lines.append("blend")
            lines.append("{")
            lines.append(f"    layer = {blend.layer}")
            lines.append(f"    mainTile = {blend.main_tile}")
            lines.append(f"    blendTile = {blend.blend_tile}")
            lines.append(f"    dir = {blend.direction}")
            if blend.exclude:
                lines.append(f"    exclude = {blend.exclude}")
            for key, value in blend.extras.items():
                lines.append(f"    {key} = {value}")
            lines.append("}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _extract_blocks(
        self, text: str, *, keyword: str
    ) -> tuple[str, List[Dict[str, str | List[str]]]]:
        lines = text.splitlines()
        idx = 0
        version = ""
        blocks: List[Dict[str, str | List[str]]] = []
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue
            if line.startswith("version"):
                _, value = line.split("=", 1)
                version = self._normalize_value(value)
                idx += 1
                continue
            if line.startswith(keyword):
                block, idx = self._parse_block(lines, idx + 1)
                if block:
                    blocks.append(block)
                continue
            idx += 1
        return version, blocks

    def _parse_block(
        self, lines: Sequence[str], start: int
    ) -> tuple[Dict[str, str | List[str]], int]:
        block: Dict[str, str | List[str]] = {}
        idx = start
        while idx < len(lines) and lines[idx].strip() != "{":
            idx += 1
        idx += 1
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue
            if line.startswith("}"):
                return block, idx + 1
            if "=" not in line:
                idx += 1
                continue
            key, rest = line.split("=", 1)
            key = key.strip()
            value = rest.strip()
            if value.startswith("["):
                values, idx = self._parse_list(value, lines, idx)
                block[key] = values
                continue
            block[key] = self._normalize_value(value)
            idx += 1
        return block, idx

    def _parse_list(
        self, first_segment: str, lines: Sequence[str], index: int
    ) -> tuple[List[str], int]:
        entries: List[str] = []
        remainder = first_segment[1:].strip()
        if remainder.endswith("]"):
            entries.extend(self._split_items(remainder[:-1]))
            return entries, index + 1
        if remainder:
            entries.extend(self._split_items(remainder))
        idx = index + 1
        while idx < len(lines):
            part = lines[idx].strip()
            if not part:
                idx += 1
                continue
            if part.endswith("]"):
                entries.extend(self._split_items(part[:-1]))
                return entries, idx + 1
            entries.extend(self._split_items(part))
            idx += 1
        return entries, idx

    @staticmethod
    def _split_items(text: str) -> List[str]:
        tokens = []
        for chunk in text.split():
            cleaned = RulesBlendsManager._normalize_value(chunk)
            if cleaned:
                tokens.append(cleaned)
        return tokens

    @staticmethod
    def _normalize_value(value: str) -> str:
        stripped = value.split("//", 1)[0].strip()
        stripped = stripped.strip('"')
        return stripped.rstrip(",")


class TileLibrary:
    """Discovers tilesets and keeps a searchable list of entries."""

    def __init__(self, search_paths: Sequence[Path]) -> None:
        self.search_paths = [Path(p) for p in search_paths]
        self.entries: List[TileEntry] = []

    def scan(self) -> None:
        self.entries.clear()
        for base in self.search_paths:
            if not base.exists():
                continue
            for path in base.rglob("*.png"):
                tileset = path.parent.name
                self.entries.append(TileEntry(name=path.stem, path=path, tileset=tileset))

    def add_search_path(self, path: Path) -> None:
        normalized = Path(path)
        if normalized not in self.search_paths:
            self.search_paths.append(normalized)
            self.scan()

    def find_best_match(self, tile_name: str) -> Optional[TileEntry]:
        token = tile_name.lower()
        ordered = sorted(self.entries, key=lambda entry: len(entry.name))
        for entry in ordered:
            candidate = entry.name.lower()
            if candidate == token:
                return entry
        for entry in ordered:
            candidate = entry.name.lower()
            if token.startswith(candidate) or candidate.startswith(token) or candidate in token:
                return entry
        return None

    def list_tiles(self) -> Iterator[TileEntry]:
        yield from sorted(self.entries, key=lambda entry: entry.display_label().lower())

    def serialize_state(self) -> str:
        return json.dumps([str(p) for p in self.search_paths], indent=2)
