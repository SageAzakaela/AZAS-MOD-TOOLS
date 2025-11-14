from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from PIL import Image

from .catalog import BuildingAsset, scan_asset_catalog
from ..utils import colors as base_colors


@dataclass(slots=True)
class RoadSample:
    x: int
    y: int
    orientation: str  # horizontal / vertical / junction / endpoint


@dataclass(slots=True)
class LotPlacement:
    x: int
    y: int
    width: int
    height: int
    orientation: str
    category: str
    asset_name: str
    asset_path: str
    metadata: Mapping[str, str | int]

    def as_conf_entry(self) -> dict[str, str | int]:
        entry = {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "type": f"{self.orientation} {self.category.title()}",
            "orientation": self.orientation,
            "category": self.category,
            "asset": self.asset_name,
            "asset_path": str(self.asset_path),
        }
        entry.update(self.metadata)
        return entry


TERRAIN_COLORS = {
    name: tuple(col[:3])
    for name, col in base_colors.VANILLA.items()
    if name
}
VEG_COLORS = {
    name: tuple(col[:3])
    for name, col in base_colors.VEG.items()
    if name
}


def generate_prototype_layout(
    lots_conf: Mapping,
    terrain_img: Image.Image | None,
    roads_img: Image.Image | None,
    veg_img: Image.Image | None = None,
) -> list[dict[str, str | int]]:
    proto_conf = (lots_conf or {}).get("prototype", {})
    enabled = proto_conf.get("enabled", False)
    if not enabled or terrain_img is None or roads_img is None:
        return []

    asset_root = Path(proto_conf.get("asset_root") or _default_asset_root())
    categories_conf = proto_conf.get("categories") or _default_category_settings()
    size_presets = proto_conf.get("size_presets") or _default_size_presets()

    assets = scan_asset_catalog(asset_root, categories_conf)
    assets_by_category = _group_assets_by_category(assets)

    for category, presets in size_presets.items():
        if assets_by_category.get(category):
            continue
        assets_by_category[category] = [
            _virtual_asset(asset_root, category, preset) for preset in presets
        ]

    road_samples = _collect_road_samples(roads_img)
    if not road_samples:
        return []

    placements: list[LotPlacement] = []
    occupied: list[tuple[int, int, int, int]] = []
    map_width, map_height = terrain_img.size
    padding_default = int(proto_conf.get("collision_padding", 6))
    attempts_default = int(proto_conf.get("attempts_per_lot", 80))

    for category, settings in categories_conf.items():
        target = int(settings.get("count", 0))
        if target <= 0:
            continue
        assets_pool = assets_by_category.get(category)
        if not assets_pool:
            continue

        padding = int(settings.get("padding_override", padding_default))
        attempts = int(settings.get("attempts_per_lot", attempts_default))
        for _ in range(target):
            placement = _try_place_lot(
                category=category,
                settings=settings,
                assets_pool=assets_pool,
                road_samples=road_samples,
                terrain_img=terrain_img,
                veg_img=veg_img,
                map_width=map_width,
                map_height=map_height,
                occupied=occupied,
                padding=padding,
                attempts=attempts,
            )
            if placement:
                placements.append(placement)
                occupied.append((placement.x, placement.y, placement.width, placement.height))

    return [placement.as_conf_entry() for placement in placements]


def _try_place_lot(
    *,
    category: str,
    settings: Mapping,
    assets_pool: Sequence[BuildingAsset],
    road_samples: Sequence[RoadSample],
    terrain_img: Image.Image,
    veg_img: Image.Image | None,
    map_width: int,
    map_height: int,
    occupied: list[tuple[int, int, int, int]],
    padding: int,
    attempts: int,
) -> LotPlacement | None:
    if not road_samples:
        return None

    terrain_pref: set[str] = set(settings.get("terrain_pref", []))
    veg_pref: set[str] = set(settings.get("vegetation_pref", []))
    distance_cfg = settings.get("road_distance") or {"min": 10, "max": 28}
    buffer_cfg = settings.get("lateral_variance") or {"min": -6, "max": 6}
    bias_orientation = settings.get("orientation_bias") or []

    for _ in range(max(1, attempts)):
        sample = random.choice(road_samples)
        facing = _pick_facing(sample.orientation, bias_orientation)
        asset = random.choice(assets_pool)

        offset = _rand_between(distance_cfg, default_min=6, default_max=20)
        lateral = _rand_between(buffer_cfg, default_min=-4, default_max=4)

        lot_x, lot_y = _project_from_road(sample.x, sample.y, asset.width, asset.height, facing, offset, lateral)
        if lot_x is None or lot_y is None:
            continue
        if not _within_bounds(lot_x, lot_y, asset.width, asset.height, map_width, map_height):
            continue
        if not _terrain_ok(terrain_img, lot_x, lot_y, asset.width, asset.height, terrain_pref):
            continue
        if veg_pref and not _vegetation_ok(veg_img, lot_x, lot_y, asset.width, asset.height, veg_pref):
            continue
        if _overlaps_existing(lot_x, lot_y, asset.width, asset.height, occupied, padding):
            continue

        metadata = {
            "stories": asset.metadata.get("stories", 1),
            "source": asset.metadata.get("source", asset.path.name),
        }
        return LotPlacement(
            x=lot_x,
            y=lot_y,
            width=asset.width,
            height=asset.height,
            orientation=facing,
            category=category,
            asset_name=asset.label,
            asset_path=str(asset.path),
            metadata=metadata,
        )
    return None


def _project_from_road(rx: int, ry: int, width: int, height: int, facing: str, offset: int, lateral: int) -> tuple[int | None, int | None]:
    if facing == "North":
        return int(rx - width / 2 + lateral), int(ry + offset)
    if facing == "South":
        return int(rx - width / 2 + lateral), int(ry - offset - height)
    if facing == "East":
        return int(rx + offset), int(ry - height / 2 + lateral)
    if facing == "West":
        return int(rx - offset - width), int(ry - height / 2 + lateral)
    return None, None


def _within_bounds(x: int, y: int, w: int, h: int, max_w: int, max_h: int) -> bool:
    return 0 <= x < max_w and 0 <= y < max_h and (x + w) <= max_w and (y + h) <= max_h


def _terrain_ok(img: Image.Image, x: int, y: int, w: int, h: int, preferred: Iterable[str]) -> bool:
    prefs = set(preferred or [])
    if not prefs:
        return True
    return any(_classify_terrain(img, px, py) in prefs for px, py in _sample_points(x, y, w, h, img.width, img.height))


def _vegetation_ok(img: Image.Image | None, x: int, y: int, w: int, h: int, preferred: Iterable[str]) -> bool:
    prefs = set(preferred or [])
    if not prefs:
        return True
    if img is None:
        return True
    return any(_classify_vegetation(img, px, py) in prefs for px, py in _sample_points(x, y, w, h, img.width, img.height))


def _sample_points(x: int, y: int, w: int, h: int, max_w: int, max_h: int) -> list[tuple[int, int]]:
    pts = [
        (x + w // 2, y + h // 2),
        (x, y),
        (x + w - 1, y),
        (x, y + h - 1),
        (x + w - 1, y + h - 1),
    ]
    clamped = [(min(max(px, 0), max_w - 1), min(max(py, 0), max_h - 1)) for px, py in pts]
    return clamped


def _classify_terrain(img: Image.Image, x: int, y: int) -> str:
    pixel = img.getpixel((x, y))[:3]
    return _closest_color(pixel, TERRAIN_COLORS)


def _classify_vegetation(img: Image.Image, x: int, y: int) -> str:
    pixel = img.getpixel((x, y))[:3]
    return _closest_color(pixel, VEG_COLORS)


def _closest_color(pixel: tuple[int, int, int], palette: Mapping[str, tuple[int, int, int]]) -> str:
    best_name = ""
    best_dist = float("inf")
    pr, pg, pb = pixel
    for name, (rr, rg, rb) in palette.items():
        dist = (pr - rr) ** 2 + (pg - rg) ** 2 + (pb - rb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def _overlaps_existing(x: int, y: int, w: int, h: int, occupied: list[tuple[int, int, int, int]], padding: int) -> bool:
    for ox, oy, ow, oh in occupied:
        if (
            x - padding < ox + ow
            and x + w + padding > ox
            and y - padding < oy + oh
            and y + h + padding > oy
        ):
            return True
    return False


def _group_assets_by_category(assets: Iterable[BuildingAsset]) -> dict[str, list[BuildingAsset]]:
    grouped: dict[str, list[BuildingAsset]] = {}
    for asset in assets:
        grouped.setdefault(asset.category, []).append(asset)
    return grouped


def _collect_road_samples(roads_img: Image.Image) -> list[RoadSample]:
    if roads_img is None:
        return []
    mask = roads_img.convert("L")
    px = mask.load()
    width, height = mask.size
    samples: list[RoadSample] = []
    for y in range(height):
        for x in range(width):
            if px[x, y] < 8:
                continue
            orientation = _infer_orientation(px, x, y, width, height)
            samples.append(RoadSample(x=x, y=y, orientation=orientation))
    return samples


def _infer_orientation(px, x: int, y: int, width: int, height: int) -> str:
    left = x > 0 and px[x - 1, y] > 0
    right = x < width - 1 and px[x + 1, y] > 0
    up = y > 0 and px[x, y - 1] > 0
    down = y < height - 1 and px[x, y + 1] > 0
    horizontal = left or right
    vertical = up or down
    if horizontal and not vertical:
        return "horizontal"
    if vertical and not horizontal:
        return "vertical"
    if horizontal and vertical:
        return "junction"
    return "endpoint"


def _pick_facing(road_orientation: str, bias: Sequence[str]) -> str:
    bias = [b for b in bias if b in {"North", "South", "East", "West"}]
    if bias and random.random() < 0.35:
        return random.choice(bias)
    if road_orientation == "horizontal":
        return random.choice(["North", "South"])
    if road_orientation == "vertical":
        return random.choice(["East", "West"])
    return random.choice(["North", "South", "East", "West"])


def _default_asset_root() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "prototype_lots"


def _virtual_asset(root: Path, category: str, preset: Mapping[str, int | str]) -> BuildingAsset:
    width = int(preset.get("width", 24))
    height = int(preset.get("height", 24))
    stories = int(preset.get("stories", 1))
    label = f"{preset.get('name', f'{category}_{width}x{height}')}"
    virtual_path = root / f"{category}_{label}.tbx"
    return BuildingAsset(
        path=virtual_path,
        category=category,
        label=label,
        width=width,
        height=height,
        stories=stories,
        metadata={"source": label, "stories": stories, "virtual": True},
    )


def _default_category_settings() -> dict[str, dict]:
    return {
        "residential": {
            "folder": "residential",
            "count": 8,
            "road_distance": {"min": 10, "max": 26},
            "terrain_pref": ["light_grass", "med_grass"],
            "vegetation_pref": ["light_long_grass", "grass_some_trees"],
        },
        "industrial": {
            "folder": "industrial",
            "count": 4,
            "road_distance": {"min": 16, "max": 40},
            "terrain_pref": ["dark_grass", "water", "med_grass"],
            "vegetation_pref": ["dense_forest", "dense_trees_grass", "trees_grass"],
        },
        "commercial": {
            "folder": "commercial",
            "count": 5,
            "road_distance": {"min": 8, "max": 18},
            "terrain_pref": ["light_asphalt", "medium_asphalt", "sand", "dirt", "light_grass"],
            "vegetation_pref": ["bushes_grass", "light_long_grass"],
        },
    }


def _default_size_presets() -> dict[str, list[dict[str, int | str]]]:
    return {
        "residential": [
            {"name": "small_house", "width": 18, "height": 20, "stories": 1},
            {"name": "mid_house", "width": 24, "height": 26, "stories": 2},
        ],
        "commercial": [
            {"name": "shop_front", "width": 30, "height": 20, "stories": 1},
            {"name": "corner_store", "width": 26, "height": 26, "stories": 2},
        ],
        "industrial": [
            {"name": "warehouse", "width": 34, "height": 34, "stories": 1},
            {"name": "factory_strip", "width": 42, "height": 24, "stories": 1},
        ],
    }


def _rand_between(cfg: Mapping[str, int], default_min: int, default_max: int) -> int:
    lo = int(cfg.get("min", default_min))
    hi = int(cfg.get("max", default_max))
    if hi < lo:
        lo, hi = hi, lo
    return random.randint(lo, hi)
