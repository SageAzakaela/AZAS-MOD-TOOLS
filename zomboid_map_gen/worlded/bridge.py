from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple
from ..config import DEFAULT_RULES

WORLD_TAIL_PATH = Path(__file__).resolve().parents[1] / "assets" / "text" / "worlded_tail.txt"
IMAGES_DIR_NAME = "images"


def project_dir_for(conf: dict, project_name: str | None = None) -> Path:
    project_dir, _, _ = _compute_project_dir(conf, project_name)
    return project_dir


def _compute_project_dir(conf: dict, project_name: str | None = None) -> tuple[Path, str, dict]:
    world_conf = conf.get("worlded", {}) or {}
    project_prefix = world_conf.get("project_prefix", "INFINITY_Z").strip() or "INFINITY_Z"
    base_name = project_name or world_conf.get("default_project_name") or _timestamp_stub()
    safe_name = _sanitize_name(base_name)
    folder_name = f"{project_prefix}_{safe_name}".strip("_")
    output_root = Path(world_conf.get("output_root", "worlded_projects")).expanduser()
    project_dir = output_root / folder_name
    return project_dir, folder_name, world_conf

@dataclass(slots=True)
class WorldEdProject:
    project_dir: Path
    pzw_path: Path

    def __str__(self) -> str:
        return str(self.project_dir)


def prepare_project(
    conf: dict,
    project_name: str | None = None,
    *,
    tiles_root_override: Path | None = None,
    reuse_tiles: bool = False,
) -> WorldEdProject:
    """
    Prepare a WorldEd-ready project folder from the latest tile export.

    Returns the path to the newly created project directory.
    """
    project_dir, folder_name, world_conf = _compute_project_dir(conf, project_name)

    subdirs = [
        IMAGES_DIR_NAME,
        "TMX",
        "LOTS",
        "BUILDINGS",
        "OBJECTS",
        "SPAWNPOINTS",
    ]
    for sub in subdirs:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    rules_src = Path(world_conf.get("rules_file", "")).expanduser()
    if not rules_src.is_file():
        if DEFAULT_RULES.exists():
            rules_src = DEFAULT_RULES
        else:
            raise FileNotFoundError(f"WorldEd rules file not found or invalid: {rules_src}")
    shutil.copy2(rules_src, project_dir / "Rules.txt")

    out_dir = Path(conf.get("output_dir", "output")).expanduser()
    exp = conf.get("export", {}) or {}
    tile_prefix = _sanitize_tile_prefix(exp.get("tile_prefix", "map"))
    tiles_root = Path(tiles_root_override) if tiles_root_override is not None else out_dir / tile_prefix
    terrain_src = tiles_root / "Terrain"
    vegetation_src = tiles_root / "Vegetation"

    cells_x, cells_y = _grid_dims(conf)
    if not terrain_src.exists():
        raise FileNotFoundError(f"Terrain tiles not found: {terrain_src}")

    images_dir = project_dir / IMAGES_DIR_NAME
    terrain_dest = images_dir
    vegetation_dest = images_dir

    rel_paths = _copy_cells(
        terrain_src,
        terrain_dest,
        src_prefix=tile_prefix,
        dest_prefix=tile_prefix,
        cells_x=cells_x,
        cells_y=cells_y,
        rel_root=IMAGES_DIR_NAME,
        copy_files=not reuse_tiles,
    )
    veg_rel_map = _copy_cells(
        vegetation_src,
        vegetation_dest,
        src_prefix=tile_prefix,
        dest_prefix=tile_prefix,
        cells_x=cells_x,
        cells_y=cells_y,
        rel_root=IMAGES_DIR_NAME,
        src_suffix="_veg",
        suffix="_veg",
        optional=True,
        copy_files=not reuse_tiles,
    )
    if not veg_rel_map:
        veg_rel_map = _copy_cells(
            terrain_src,
            vegetation_dest,
            src_prefix=tile_prefix,
            dest_prefix=tile_prefix,
            cells_x=cells_x,
            cells_y=cells_y,
            rel_root=IMAGES_DIR_NAME,
            src_suffix="_veg",
            suffix="_veg",
            optional=True,
            copy_files=not reuse_tiles,
        )

    rules_rel = "Rules.txt"
    tmx_rel = "TMX"

    width, height = _determine_dimensions(rel_paths, cells_x, cells_y)

    bmp_entries = [
        f' <bmp path="{rel_paths[(x, y)]}" x="{x}" y="{y}" width="1" height="1"/>'
        for y in range(height)
        for x in range(width)
        if (x, y) in rel_paths
    ]

    pzw_content = _build_pzw(
        width=width,
        height=height,
        bmp_entries=bmp_entries,
        rules_path=rules_rel,
        tmx_export_dir=tmx_rel,
        assign_maps=bool(world_conf.get("assign_maps", True)),
        update_existing=bool(world_conf.get("update_existing", world_conf.get("replace_existing", True))),
    )

    pzw_path = project_dir / f"{folder_name}.pzw"
    pzw_path.write_text(pzw_content, encoding="utf-8")
    return WorldEdProject(project_dir=project_dir, pzw_path=pzw_path)


def _grid_dims(conf: dict) -> Tuple[int, int]:
    canvas = conf.get("canvas", {}) or {}
    cells_x = max(1, int(canvas.get("cells_x", 1)))
    cells_y = max(1, int(canvas.get("cells_y", 1)))
    return cells_x, cells_y


def _determine_dimensions(rel_paths: dict[tuple[int, int], str], default_x: int, default_y: int) -> Tuple[int, int]:
    if not rel_paths:
        return default_x, default_y
    max_x = max(x for x, _ in rel_paths.keys())
    max_y = max(y for _, y in rel_paths.keys())
    return max(max_x + 1, default_x), max(max_y + 1, default_y)


def _copy_cells(
    src_dir: Path,
    dest_dir: Path,
    src_prefix: str,
    dest_prefix: str,
    cells_x: int,
    cells_y: int,
    *,
    rel_root: str,
    src_suffix: str = "",
    suffix: str = "",
    optional: bool = False,
    copy_files: bool = True,
) -> dict[tuple[int, int], str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    rel_map: dict[tuple[int, int], str] = {}
    missing: list[Path] = []

    for y in range(cells_y):
        for x in range(cells_x):
            src_name = f"{src_prefix}_{x}_{y}{src_suffix}.png"
            src_path = src_dir / src_name
            if not src_path.exists():
                if optional:
                    continue
                missing.append(src_path)
                continue

            dest_name = f"{dest_prefix}_{x}_{y}{suffix}.png"
            dest_path = dest_dir / dest_name
            if src_path != dest_path and (copy_files or not dest_path.exists()):
                shutil.copy2(src_path, dest_path)
            if not dest_path.exists():
                missing.append(dest_path)
                continue
            rel_map[(x, y)] = f"{rel_root}/{dest_name}".replace("\\", "/")

    if missing and not optional:
        missing_list = "\n".join(str(p) for p in missing[:5])
        raise FileNotFoundError(f"Missing terrain tiles:\n{missing_list}")

    if not rel_map and not optional:
        raise RuntimeError("No terrain tiles were copied; check the export step.")

    return rel_map



def _build_pzw(
    *,
    width: int,
    height: int,
    bmp_entries: list[str],
    rules_path: str,
    tmx_export_dir: str,
    assign_maps: bool,
    update_existing: bool,
) -> str:
    tail = WORLD_TAIL_PATH.read_text(encoding="utf-8")
    assign_flag = "true" if assign_maps else "false"
    update_flag = "true" if update_existing else "false"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<world version="1.0" width="{width}" height="{height}">',
        " <BMPToTMX>",
        f'  <tmxexportdir path="{tmx_export_dir}"/>',
        f'  <rulesfile path="{rules_path}"/>',
        '  <blendsfile path=""/>',
        '  <mapbasefile path=""/>',
        f'  <assign-maps-to-world checked="{assign_flag}"/>',
        '  <warn-unknown-colors checked="true"/>',
        '  <compress checked="true"/>',
        '  <copy-pixels checked="true"/>',
        f'  <update-existing checked="{update_flag}"/>',
        " </BMPToTMX>",
        " <TMXToBMP>",
        '  <mainImage generate="true"/>',
        '  <vegetationImage generate="true"/>',
        '  <buildingsImage path="" generate="false"/>',
        " </TMXToBMP>",
        " <GenerateLots>",
        '  <exportdir path=""/>',
        '  <ZombieSpawnMap path=""/>',
        '  <TileDefFolder path=""/>',
        '  <worldOrigin origin="0,0"/>',
        " </GenerateLots>",
        " <LuaSettings>",
        '  <spawnPointsFile path=""/>',
        '  <worldObjectsFile path=""/>',
        " </LuaSettings>",
    ]
    lines.extend(bmp_entries)
    lines.append(tail.strip("\ufeff\n\r"))
    return "\n".join(lines) + ("\n" if not tail.endswith("\n") else "")


def _sanitize_tile_prefix(prefix: str) -> str:
    candidate = (prefix or "").strip()
    sanitized = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in candidate)
    return sanitized or "map"


def _sanitize_name(name: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or "").strip())
    return clean or _timestamp_stub()


def _timestamp_stub() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
