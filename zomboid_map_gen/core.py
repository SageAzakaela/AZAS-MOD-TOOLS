# zomboid_map_gen/core.py
from pathlib import Path
from . import config as cfg
from .terrain import terrain_generator
from .vegetation import vegetation_generator
from .roads import road_generator
from .roads import road_post
from .lots import prototype as lots_prototype
from .export import writer
from .vegetation import detail_generator
from .utils import colors as base_colors
from .utils import rules_palette as rules_palette_utils
from PIL import Image, ImageDraw
import json
from typing import Callable

def generate_from_config(conf: dict):
    base_colors.apply_palette_overrides(conf.get("terrain", {}).get("palette"))
    out_dir = Path(conf.get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    terrain_img = terrain_generator.generate(conf) if conf.get("terrain", {}).get("enabled", True) else None
    veg_img = vegetation_generator.generate(conf, terrain_img) if conf.get("vegetation", {}).get("enabled", True) else None
    roads_img, lots_img = road_generator.generate(conf, terrain_img, veg_img) if conf.get("roads", {}).get("enabled", True) else (None, None)

    # Optional details bitmap based on rules (terrain/veg/roads aware)
    details_img = None
    try:
        if conf.get("details", {}).get("enabled", True):
            w, h = (terrain_img.size if terrain_img is not None else (None, None))
            if w and h:
                details_img = detail_generator.generate(conf, w, h, terrain_img, veg_img, roads_img)
    except Exception:
        details_img = None

    terrain_img, veg_img, details_img = _apply_rules_palette(conf, terrain_img, veg_img, details_img)

    # Optional: carve vegetation where roads are present (punch out trees on roads)
    if veg_img is not None and roads_img is not None:
        road_post.carve_vegetation_mask(veg_img, roads_img, skip_dirt=True)

    # Apply details onto vegetation if enabled
    if veg_img is not None and details_img is not None:
        if conf.get("details", {}).get("apply_to_vegetation", True):
            veg_img = veg_img.copy()
            veg_img.alpha_composite(details_img.convert("RGBA"))

    lots_img = _generate_lots_overlay(conf, terrain_img, veg_img, roads_img)
    writer.save_all(conf, terrain_img, veg_img, roads_img, lots_img, details_img)


def _conf_for_cell(conf: dict, cell_x: int, cell_y: int) -> dict:
    copy = json.loads(json.dumps(conf))
    canvas = copy.setdefault("canvas", {})
    cell_size = int(canvas.get("cell_size", 300))
    canvas["cells_x"] = 1
    canvas["cells_y"] = 1
    offx = int(cell_x) * cell_size
    offy = int(cell_y) * cell_size

    def bump(section: str):
        sec = copy.setdefault(section, {})
        tr = sec.setdefault("transform", {})
        tr["offset_x"] = float(tr.get("offset_x", 0.0)) + offx
        tr["offset_y"] = float(tr.get("offset_y", 0.0)) + offy

    bump("terrain")
    bump("vegetation")
    return copy


def generate_preview_from_config(conf: dict, cell_x: int = 0, cell_y: int = 0):
    """Generate a fast preview by rendering only one cell.

    - Keeps noise alignment stable by offsetting transforms by the cell origin
    - Writes the same output files (terrain/vegetation/roads/etc) and preview.png
    """
    c2 = _conf_for_cell(conf, cell_x, cell_y)
    return generate_from_config(c2)


LOT_COLOR_MAP = {
    "North Residential": (0, 139, 139),
    "East Residential": (0, 100, 0),
    "South Residential": (139, 0, 0),
    "West Residential": (139, 0, 139),
    "North Industrial": (0, 206, 209),
    "East Industrial": (60, 179, 113),
    "South Industrial": (205, 92, 92),
    "West Industrial": (199, 21, 133),
    "North Commercial": (224, 255, 255),
    "East Commercial": (144, 238, 144),
    "South Commercial": (255, 182, 193),
    "West Commercial": (255, 119, 255),
}


def _generate_lots_overlay(conf: dict, terrain_img, veg_img, roads_img=None):
    lots_conf = conf.get("lots", {}) or {}
    mode = lots_conf.get("mode", "manual") or "manual"
    placed = lots_conf.get("placed", []) or []

    if mode == "prototype":
        placed = lots_prototype.generate_prototype_layout(lots_conf, terrain_img, roads_img, veg_img)

    if not placed or terrain_img is None:
        return None

    mask = lots_conf.get("mask_vegetation", False)
    pave = lots_conf.get("pave", False)
    width, height = terrain_img.size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for lot in placed:
        x, y = lot.get("x", 0), lot.get("y", 0)
        w, h = lot.get("width", 0), lot.get("height", 0)
        color = LOT_COLOR_MAP.get(lot.get("type", ""), (255, 255, 255))
        if pave:
            color = (210, 210, 210)
        x2, y2 = x + w, y + h
        if mask and veg_img:
            px = min(max(x, 0), veg_img.width - 1)
            py = min(max(y, 0), veg_img.height - 1)
            if veg_img.getpixel((px, py))[3] > 0:
                continue
        draw.rectangle([x, y, x2, y2], fill=color + (160,))
    return img


def _apply_rules_palette(conf: dict, terrain_img, veg_img, details_img):
    replacements = rules_palette_utils.build_palette_replacements(conf)
    terrain_repl = replacements.get("terrain", {})
    if terrain_repl and terrain_img is not None:
        terrain_img = rules_palette_utils.recolor_image(terrain_img, terrain_repl)
    veg_repl = replacements.get("vegetation", {})
    if veg_repl:
        if veg_img is not None:
            veg_img = rules_palette_utils.recolor_image(veg_img, veg_repl)
        if details_img is not None:
            details_img = rules_palette_utils.recolor_image(details_img, veg_repl)
    return terrain_img, veg_img, details_img


def generate_tiles(conf: dict, prefix: str, progress: Callable[[int, int], None] | None = None, *,
                   tile_root_override: Path | None = None):
    canvas = conf.get("canvas", {})
    cells_x = max(1, int(canvas.get("cells_x", 1)))
    cells_y = max(1, int(canvas.get("cells_y", 1)))
    out_dir = Path(conf.get("output_dir", "output"))
    sanitized = _sanitize_prefix(prefix)
    tiles_root = Path(tile_root_override) if tile_root_override is not None else out_dir / sanitized
    terrain_dir = tiles_root / "Terrain"
    veg_dir = tiles_root / "Vegetation"
    roads_dir = tiles_root / "Roads"
    for d in (terrain_dir, veg_dir, roads_dir):
        d.mkdir(parents=True, exist_ok=True)

    full_conf = json.loads(json.dumps(conf))
    generate_from_config(full_conf)

    exp = full_conf.get("export", {})
    combined_path = out_dir / exp.get("combined_png", "combined.png")
    preview_path = out_dir / exp.get("preview_png", "preview.png")
    if not combined_path.exists():
        if preview_path.exists():
            combined_path = preview_path
        else:
            raise FileNotFoundError(
                f"Tile export needs a combined or preview image but none were created in {out_dir}; "
                "ensure terrain/roads generation wasn't disabled."
            )
    veg_full = out_dir / exp.get("vegetation_png", "vegetation.png")
    roads_full = out_dir / exp.get("roads_png", "roads.png")

    combo_img = Image.open(combined_path)
    veg_img = Image.open(veg_full) if veg_full.exists() else None
    roads_img = Image.open(roads_full) if roads_full.exists() else None

    total = cells_x * cells_y
    idx = 0
    size = int(canvas.get("cell_size", 300))
    for y in range(cells_y):
        for x in range(cells_x):
            idx += 1
            box = (x * size, y * size, min((x + 1) * size, combo_img.width), min((y + 1) * size, combo_img.height))
            tile_combined = combo_img.crop(box)
            tile_combined.save(terrain_dir / f"{sanitized}_{x}_{y}.png")
            if veg_img:
                veg_tile = veg_img.crop(box)
                veg_tile.save(veg_dir / f"{sanitized}_{x}_{y}_veg.png")
            if roads_img:
                road_tile = roads_img.crop(box)
                road_tile.save(roads_dir / f"{sanitized}_roads_{x}_{y}.png")
            if progress:
                progress(idx, total)
    combo_img.close()
    if veg_img:
        veg_img.close()
    if roads_img:
        roads_img.close()


def _sanitize_prefix(prefix: str) -> str:
    candidate = (prefix or "").strip()
    sanitized = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in candidate)
    return sanitized or "tiles"
