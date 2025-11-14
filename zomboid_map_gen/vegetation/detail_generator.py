# Begin ignored block (docstring to neutralize problematic label strings)
r'''
Detail bitmap generator driven by terrain/vegetation/roads context.

Outputs a color-coded PNG (details.png) intended to be consumed by
WorldEd Rules.txt. Each configured rule paints its associated RGB color
at eligible pixels based on simple predicates and noise density.

Config shape (example):

details: {
  enabled: true,
  layers: [
    {
      name: "flowers_light_grass",
      rule_color: [240, 200, 160],  # must match Rules.txt rule color
      density: 0.06,
      scale: 55, seed: 10,
      terrain_in: ["light_grass"],
    },
    {
      name: "trash_on_asphalt",
      rule_color: [160,130,95],
      density: 0.05,
      scale: 42, seed: 20,
      road_mode: "asphalt_only",  # {asphalt_only, non_asphalt, any}
    },
  ]
}
r'''

from PIL import Image
from typing import Optional
from pathlib import Path
import re
import unicodedata
from ..utils import colors as base_colors
from ..utils import noise_utils, seeds as seed_utils


ASPHALT_SET = {
    base_colors.VANILLA["light_asphalt"][:3],
    base_colors.VANILLA["medium_asphalt"][:3],
    base_colors.VANILLA["dark_asphalt"][:3],
}

TERRAIN_KEYS = {
    "dark_grass": base_colors.VANILLA["dark_grass"][:3],
    "med_grass": base_colors.VANILLA["med_grass"][:3],
    "light_grass": base_colors.VANILLA["light_grass"][:3],
    "sand": base_colors.VANILLA["sand"][:3],
    "dirt": base_colors.VANILLA["dirt"][:3],
}


def _closest_terrain_name(rgb):
    # simple L1 distance across our limited set
    best = None; bestd = 1e9
    for name, col in TERRAIN_KEYS.items():
        d = abs(rgb[0]-col[0]) + abs(rgb[1]-col[1]) + abs(rgb[2]-col[2])
        if d < bestd:
            bestd = d; best = name
    return best


def _roads_pixel_mode(px):
    if px is None:
        return "none"
    if len(px) == 4 and px[3] == 0:
        return "none"
    rgb = px[:3]
    return "asphalt" if rgb in ASPHALT_SET else "non_asphalt"


def _rules_file_path() -> Path:
    base = Path(__file__).resolve()
    pkg_path = base.parents[1] / "assets" / "text" / "Rules.txt"
    if pkg_path.exists():
        return pkg_path
    return base.parents[2] / "assets" / "text" / "Rules.txt"


def _color_from_rules_label(label: str) -> Optional[tuple[int, int, int]]:
    # First try a direct regex search using the given label.
    try:
        txt = _rules_file_path().read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    pattern = re.compile(r"label\s*=\s*" + re.escape(label) + r"[\s\S]*?color\s*=\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)", re.IGNORECASE)
    m = pattern.search(txt)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (r, g, b)

    # If exact search fails (encoding/punctuation mismatch), build a normalized
    # label->color index for the whole file and try a fuzzy lookup.
    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s)
        s = s.encode("ascii", "ignore").decode("ascii")
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    want = _norm(label)
    cur_label = None
    for line in txt.splitlines():
        line = line.strip()
        if line.lower().startswith("label"):
            cur_label = line.split("=", 1)[1].strip() if "=" in line else None
        elif line.lower().startswith("color") and cur_label:
            parts = re.findall(r"\d+", line)
            if len(parts) >= 3:
                col = (int(parts[0]), int(parts[1]), int(parts[2]))
                if _norm(cur_label) == want:
                    return col
            cur_label = None
        elif line.startswith("}"):
            cur_label = None
    return None


def _colors_for_labels(labels: list[str]) -> list[tuple[int, int, int]]:
    out = []
    for lab in labels:
        c = _color_from_rules_label(lab)
        if c:
            out.append(c)
    return out


QUICK_LABELS = {
    # compact groups of labels pulled from your list
    "flowers": [
        "Flowers – Orange (Dense)", "Flowers – Orange (Medium)", "Flowers – Orange (Sparse)",
        "Flowers – Yellow (Dense)", "Flowers – Yellow (Medium)", "Flowers – Yellow (Sparse)",
        "Flowers – Pink Low (Dense)", "Flowers – Pink Low (Medium)", "Flowers – Pink Low (Sparse)",
        "Flowers – Tall Pale (Dense)", "Flowers – Tall Pale (Medium)", "Flowers – Tall Pale (Sparse)",
        "Flowers – Purple (Dense)", "Flowers – Purple (Medium)", "Flowers – Purple (Sparse)",
        "Flowers – White (Dense)", "Flowers – White (Medium)", "Flowers – White (Sparse)",
        "Flowers – Tiny Warm (Dense)", "Flowers – Tiny Warm (Medium)", "Flowers – Tiny Warm (Sparse)",
        "Flowers – Tiny Cool (Dense)", "Flowers – Tiny Cool (Medium)", "Flowers – Tiny Cool (Sparse)",
    ],
    "leaves": [
        "Fallen Leaves (Dense)", "Fallen Leaves (Medium)", "Fallen Leaves (Sparse)",
    ],
    "trash": [
        "Street Trash – Papers (Dense)", "Street Trash – Papers (Medium)", "Street Trash – Papers (Sparse)",
        "Street Trash – Bulk (Dense)", "Street Trash – Bulk (Medium)", "Street Trash – Bulk (Sparse)",
        "Street Trash – Small Scatter (Dense)", "Street Trash – Small Scatter (Medium)", "Street Trash – Small Scatter (Sparse)",
        "Ground Trash (Dense)", "Ground Trash (Medium)", "Ground Trash (Sparse)",
        "Broken Glass (Dense)", "Broken Glass (Medium)", "Broken Glass (Sparse)",
        "Grimy Street Mix",
    ],
    "cracks": [
        "Street Cracks – Small (Dense)", "Street Cracks – Small (Medium)", "Street Cracks – Small (Sparse)",
        "Street Cracks – Medium (Dense)", "Street Cracks – Medium (Medium)", "Street Cracks – Medium (Sparse)",
        "Street Cracks – Heavy (Dense)", "Street Cracks – Heavy (Medium)", "Street Cracks – Heavy (Sparse)",
    ],
    "blood": ["Blood – Heavy", "Blood – Medium", "Blood – Sparse"],
    "forest_floor": [
        "Forest Floor – Sprouts (Dense)", "Forest Floor – Sprouts (Medium)", "Forest Floor – Sprouts (Sparse)",
        "Forest Floor – Fallen Branches (Dense)", "Forest Floor – Fallen Branches (Medium)", "Forest Floor – Fallen Branches (Sparse)",
        "Forest Floor – Roots & Shoots (Dense)", "Forest Floor – Roots & Shoots (Medium)", "Forest Floor – Roots & Shoots (Sparse)",
        "Forest Floor – Rocks & Duff (Dense)", "Forest Floor – Rocks & Duff (Medium)", "Forest Floor – Rocks & Duff (Sparse)",
        "Forest Floor – Low Ferns (Dense)", "Forest Floor – Low Ferns (Medium)", "Forest Floor – Low Ferns (Sparse)",
        "Forest Floor – Twigs (Dense)", "Forest Floor – Twigs (Medium)", "Forest Floor – Twigs (Sparse)",
        "Forest Floor – Light Scatter (Dense)", "Forest Floor – Light Scatter (Medium)", "Forest Floor – Light Scatter (Sparse)",
        "Forest Floor – Deep Layer (Dense)", "Forest Floor – Deep Layer (Medium)", "Forest Floor – Deep Layer (Sparse)",
    ],
}

"""
# Extend quick labels with additional families for finer control
_QUICK_LABELS_EXTRA = {
    # Flowers families
    "flowers_orange": [
        "Flowers �?" Orange (Dense)", "Flowers �?" Orange (Medium)", "Flowers �?" Orange (Sparse)",
    ],
    "flowers_yellow": [
        "Flowers �?" Yellow (Dense)", "Flowers �?" Yellow (Medium)", "Flowers �?" Yellow (Sparse)",
    ],
    "flowers_pink_low": [
        "Flowers �?" Pink Low (Dense)", "Flowers �?" Pink Low (Medium)", "Flowers �?" Pink Low (Sparse)",
    ],
    "flowers_tall_pale": [
        "Flowers �?" Tall Pale (Dense)", "Flowers �?" Tall Pale (Medium)", "Flowers �?" Tall Pale (Sparse)",
    ],
    "flowers_purple": [
        "Flowers �?" Purple (Dense)", "Flowers �?" Purple (Medium)", "Flowers �?" Purple (Sparse)",
    ],
    "flowers_white": [
        "Flowers �?" White (Dense)", "Flowers �?" White (Medium)", "Flowers �?" White (Sparse)",
    ],
    "flowers_tiny_warm": [
        "Flowers �?" Tiny Warm (Dense)", "Flowers �?" Tiny Warm (Medium)", "Flowers �?" Tiny Warm (Sparse)",
    ],
    "flowers_tiny_cool": [
        "Flowers �?" Tiny Cool (Dense)", "Flowers �?" Tiny Cool (Medium)", "Flowers �?" Tiny Cool (Sparse)",
    ],

    # Forest floor families
    "forest_sprouts": [
        "Forest Floor �?" Sprouts (Dense)", "Forest Floor �?" Sprouts (Medium)", "Forest Floor �?" Sprouts (Sparse)",
    ],
    "forest_branches": [
        "Forest Floor �?" Fallen Branches (Dense)", "Forest Floor �?" Fallen Branches (Medium)", "Forest Floor �?" Fallen Branches (Sparse)",
    ],
    "forest_roots_shoots": [
        "Forest Floor �?" Roots & Shoots (Dense)", "Forest Floor �?" Roots & Shoots (Medium)", "Forest Floor �?" Roots & Shoots (Sparse)",
    ],
    "forest_rocks_duff": [
        "Forest Floor �?" Rocks & Duff (Dense)", "Forest Floor �?" Rocks & Duff (Medium)", "Forest Floor �?" Rocks & Duff (Sparse)",
    ],
    "forest_low_ferns": [
        "Forest Floor �?" Low Ferns (Dense)", "Forest Floor �?" Low Ferns (Medium)", "Forest Floor �?" Low Ferns (Sparse)",
    ],
    "forest_twigs": [
        "Forest Floor �?" Twigs (Dense)", "Forest Floor �?" Twigs (Medium)", "Forest Floor �?" Twigs (Sparse)",
    ],
    "forest_light_scatter": [
        "Forest Floor �?" Light Scatter (Dense)", "Forest Floor �?" Light Scatter (Medium)", "Forest Floor �?" Light Scatter (Sparse)",
    ],
    "forest_deep_layer": [
        "Forest Floor �?" Deep Layer (Dense)", "Forest Floor �?" Deep Layer (Medium)", "Forest Floor �?" Deep Layer (Sparse)",
    ],

    # Trash/urban families
    "trash_papers": [
        "Street Trash �?" Papers (Dense)", "Street Trash �?" Papers (Medium)", "Street Trash �?" Papers (Sparse)",
    ],
    "trash_bulk": [
        "Street Trash �?" Bulk (Dense)", "Street Trash �?" Bulk (Medium)", "Street Trash �?" Bulk (Sparse)",
    ],
    "trash_small_scatter": [
        "Street Trash �?" Small Scatter (Dense)", "Street Trash �?" Small Scatter (Medium)", "Street Trash �?" Small Scatter (Sparse)",
    ],
    "trash_ground": [
        "Ground Trash (Dense)", "Ground Trash (Medium)", "Ground Trash (Sparse)",
    ],
    "trash_glass": [
        "Broken Glass (Dense)", "Broken Glass (Medium)", "Broken Glass (Sparse)",
    ],
    "trash_grimy_mix": [
        "Grimy Street Mix",
    ],

    # Street cracks families
    "cracks_small": [
        "Street Cracks �?" Small (Dense)", "Street Cracks �?" Small (Medium)", "Street Cracks �?" Small (Sparse)",
    ],
    "cracks_medium": [
        "Street Cracks �?" Medium (Dense)", "Street Cracks �?" Medium (Medium)", "Street Cracks �?" Medium (Sparse)",
    ],
    "cracks_heavy": [
        "Street Cracks �?" Heavy (Dense)", "Street Cracks �?" Heavy (Medium)", "Street Cracks �?" Heavy (Sparse)",
    ],
}
"""

# Note: Extended QUICK_LABELS families are handled via fallbacks and do not
# require injecting additional label strings here.

# Fallback colors if labels cannot be resolved for quick items
QUICK_FALLBACK = {
    "flowers": (240, 200, 160),
    "leaves": (205, 95, 35),
    "trash": (160, 130, 95),
    "cracks": (115, 115, 115),
    "blood": (150, 0, 0),
    "forest_floor": (24, 125, 92),
}

# Extend fallback palette for new families
try:
    QUICK_FALLBACK.update({
        # flowers
        "flowers_orange": (37, 135, 95),
        "flowers_yellow": (43, 150, 105),
        "flowers_pink_low": (49, 165, 120),
        "flowers_tall_pale": (55, 180, 135),
        "flowers_purple": (61, 195, 150),
        "flowers_white": (67, 210, 165),
        "flowers_tiny_warm": (73, 225, 180),
        "flowers_tiny_cool": (79, 240, 195),
        # forest floor
        "forest_sprouts": (12, 65, 62),
        "forest_branches": (14, 75, 67),
        "forest_roots_shoots": (16, 85, 72),
        "forest_rocks_duff": (18, 95, 77),
        "forest_low_ferns": (20, 105, 82),
        "forest_twigs": (22, 115, 87),
        "forest_light_scatter": (24, 125, 92),
        "forest_deep_layer": (26, 135, 97),
        # trash/urban
        "trash_papers": (145, 110, 75),
        "trash_bulk": (135, 95, 65),
        "trash_small_scatter": (160, 130, 95),
        "trash_ground": (125, 85, 55),
        "trash_glass": (155, 205, 215),
        "trash_grimy_mix": (135, 120, 105),
        # cracks
        "cracks_small": (95, 95, 95),
        "cracks_medium": (110, 110, 110),
        "cracks_heavy": (125, 125, 125),
        # veg markers (magenta overlays)
        "bushes_dark": (255, 0, 255),
        "bushes_medium": (255, 0, 255),
        "bushes_light": (255, 0, 255),
    })
except Exception:
    pass


def generate(conf: dict, width: int, height: int,
             terrain_img: Optional[Image.Image] = None,
             veg_img: Optional[Image.Image] = None,
             roads_img: Optional[Image.Image] = None) -> Optional[Image.Image]:
    det_conf = conf.get("details", {})
    if not det_conf or not det_conf.get("enabled", True):
        return None

    layers = det_conf.get("layers", [])

    # Transparent base so it can overlay vegetation and preview
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    opx = out.load()
    tpx = terrain_img.load() if terrain_img else None
    rpx = roads_img.load() if roads_img else None
    vpx = veg_img.load() if veg_img else None

    # Build job list: advanced layers + quick items
    jobs = []
    for L in layers:
        if L.get("enabled", True):
            jobs.append(L)

    quick = det_conf.get("quick", {})
    def _add_quick(name, defaults):
        q = quick.get(name, {})
        if not q or not q.get("enabled", False):
            return
        d = float(q.get("density", defaults.get("density", 0.02)))
        if d <= 0:
            return
        job = defaults.copy(); job.update(q); job["density"] = d
        # Ensure a visible fallback color if rule labels fail to resolve.
        job.setdefault("rule_color", QUICK_FALLBACK.get(name, (255, 0, 255)))
        # Default quick items to points sampling for more predictable coverage
        job.setdefault("sampling", "points")
        jobs.append(job)

    if quick:
        _add_quick("flowers", {
            "rule_labels": QUICK_LABELS.get("flowers", []),
            "terrain_in": ["light_grass","med_grass","dark_grass"],
            "group_size_min": 1, "group_size_max": 2, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 55,
        })
        # Individual flower families
        for fam in ("flowers_orange","flowers_yellow","flowers_pink_low","flowers_tall_pale","flowers_purple","flowers_white","flowers_tiny_warm","flowers_tiny_cool"):
            _add_quick(fam, {
                "rule_labels": QUICK_LABELS.get(fam, []),
                "terrain_in": ["light_grass","med_grass","dark_grass"],
                "group_size_min": 1, "group_size_max": 2, "cluster_radius": 2, "stride": 3, "jitter": 1,
                "scale": 55,
            })
        _add_quick("leaves", {
            "rule_labels": QUICK_LABELS.get("leaves", []),
            "veg_in": ["trees_grass","dense_trees_grass","dense_forest","fir_trees_grass"],
            "near_radius": 3,
            "group_size_min": 2, "group_size_max": 5, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 70,
        })
        # Trash/urban families
        for fam in ("trash_papers","trash_bulk","trash_small_scatter","trash_ground","trash_glass","trash_grimy_mix"):
            _add_quick(fam, {
                "rule_labels": QUICK_LABELS.get(fam, []),
                "road_mode": "asphalt_only",
                "near_road_radius": 1,
                "group_size_min": 2, "group_size_max": 4, "cluster_radius": 2, "stride": 3, "jitter": 2,
                "scale": 42,
            })
        # Street cracks families
        for fam in ("cracks_small","cracks_medium","cracks_heavy"):
            _add_quick(fam, {
                "rule_labels": QUICK_LABELS.get(fam, []),
                "road_mode": "asphalt_only",
                "group_size_min": 1, "group_size_max": 1, "cluster_radius": 1, "stride": 2, "jitter": 0,
                "scale": 46,
            })
        _add_quick("blood", {
            "rule_labels": QUICK_LABELS.get("blood", []),
            "road_mode": "asphalt_only",
            "near_road_radius": 2,
            "group_size_min": 1, "group_size_max": 3, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 38,
        })
        # Forest floor families
        for fam in ("forest_sprouts","forest_branches","forest_roots_shoots","forest_rocks_duff","forest_low_ferns","forest_twigs","forest_light_scatter","forest_deep_layer"):
            _add_quick(fam, {
                "rule_labels": QUICK_LABELS.get(fam, []),
                "veg_in": ["dense_trees_grass","dense_forest"],
                "near_radius": 3,
                "group_size_min": 1, "group_size_max": 3, "cluster_radius": 2, "stride": 3, "jitter": 1,
                "scale": 55,
            })

        # Vegetation marker overlays (magenta) by terrain tint
        _add_quick("bushes_dark", {
            "rule_labels": [],
            "rule_color": QUICK_FALLBACK.get("bushes_dark"),
            "terrain_in": ["dark_grass"],
            "group_size_min": 2, "group_size_max": 4, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 60,
        })
        _add_quick("bushes_medium", {
            "rule_labels": [],
            "rule_color": QUICK_FALLBACK.get("bushes_medium"),
            "terrain_in": ["med_grass"],
            "group_size_min": 2, "group_size_max": 4, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 60,
        })
        _add_quick("bushes_light", {
            "rule_labels": [],
            "rule_color": QUICK_FALLBACK.get("bushes_light"),
            "terrain_in": ["light_grass"],
            "group_size_min": 2, "group_size_max": 4, "cluster_radius": 2, "stride": 3, "jitter": 1,
            "scale": 60,
        })

    if not jobs:
        return None

    multiplier = float(det_conf.get("density_multiplier", 1.0))
    WATER = base_colors.VANILLA["water"][:3]
    for layer in jobs:
        if not layer.get("enabled", True):
            continue
        # resolve color(s): allow rule_labels list for variety
        colors_list = []
        if layer.get("rule_labels"):
            colors_list = _colors_for_labels(layer.get("rule_labels", []))
        color = None
        if not colors_list:
            if layer.get("rule_label"):
                c = _color_from_rules_label(str(layer.get("rule_label")))
                if c:
                    color = c
            if color is None:
                color = tuple(layer.get("rule_color", (0, 0, 0)))
            if color == (0, 0, 0):
                continue
        density = float(layer.get("density", 0.02)) * multiplier
        scale = float(layer.get("scale", 60))
        octaves = int(layer.get("octaves", 4))
        persistence = float(layer.get("persistence", 0.5))
        lacunarity = float(layer.get("lacunarity", 2.0))
        seed = layer.get("seed")
        if seed is None:
            seed = seed_utils.derive_seed(conf.get("seed", 0), layer.get("name", "detail"))

        road_mode = (layer.get("road_mode", "any") or "any").lower()
        terr_in = set(layer.get("terrain_in", []))
        veg_in_names = set(layer.get("veg_in", []))
        veg_in_colors = {base_colors.VEG.get(k, None) for k in veg_in_names}
        veg_in_colors = {c[:3] for c in veg_in_colors if c}
        near_radius = int(layer.get("near_radius", 0))
        near_road_radius = int(layer.get("near_road_radius", 0))

        # threshold derived from density (higher density -> easier threshold)
        # We normalize per layer using a quick min/max pass.
        vmin = 1e9; vmax = -1e9
        sample_mode = (layer.get("sampling", "noise") or "noise").lower()
        if sample_mode == "noise":
            for x in range(width):
                for y in range(height):
                    v = noise_utils.perlin2(x, y, scale=scale, octaves=octaves,
                                            persistence=persistence, lacunarity=lacunarity, seed=seed)
                    if v < vmin: vmin = v
                    if v > vmax: vmax = v
            vr = (vmax - vmin) or 1.0
            if "threshold" in layer:
                thresh = float(layer["threshold"])  # 0..1 after normalization
            else:
                thresh = 1.0 - max(0.0, min(1.0, density))

        # Cluster parameters for tiny groups
        gmin = int(layer.get("group_size_min", 1))
        gmax = int(layer.get("group_size_max", 3))
        radius = int(layer.get("cluster_radius", 2))
        stride = max(1, int(layer.get("stride", 3)))
        # Scan at stride intervals to avoid saturating coverage
        rnd = seed_utils.derive_seed(seed, "detail_rnd")
        import random as _random
        rr = _random.Random(rnd)

        jitter = int(layer.get("jitter", 0))
        if sample_mode == "points" or int(layer.get("points", 0)) > 0:
            # points-based sampling: pick N random seeds then spawn clusters
            pts = int(layer.get("points", 0))
            if pts <= 0:
                # heuristic: approximate scan density with stride; scale by multiplier
                scan_sites = (width // stride) * (height // stride)
                pts = max(1, int(scan_sites * max(0.0, min(1.0, density)) * multiplier))
            else:
                pts = max(1, int(pts * max(0.0, multiplier)))

            attempts_per_point = 8
            for _ in range(pts):
                placed = False
                for _try in range(attempts_per_point):
                    x = rr.randrange(width)
                    y = rr.randrange(height)
                    if tpx is not None and tpx[x, y][:3] == WATER:
                        continue
                    # road filter
                    if road_mode != "any" and rpx is not None:
                        m = _roads_pixel_mode(rpx[x, y])
                        if road_mode == "asphalt_only" and m != "asphalt":
                            continue
                        if road_mode == "non_asphalt" and m != "non_asphalt":
                            continue
                    if near_road_radius > 0 and rpx is not None:
                        ok_road = False
                        for yy in range(max(0, y-near_road_radius), min(height, y+near_road_radius+1)):
                            for xx in range(max(0, x-near_road_radius), min(width, x+near_road_radius+1)):
                                if rpx[xx, yy][3] > 0:
                                    ok_road = True; break
                            if ok_road: break
                        if not ok_road:
                            continue

                    # terrain inclusion
                    if terr_in and tpx is not None:
                        tname = _closest_terrain_name(tpx[x, y][:3])
                        if tname not in terr_in:
                            continue

                    # vegetation inclusion (exact match or nearby within radius)
                    if veg_in_colors and vpx is not None:
                        ok = False
                        if near_radius <= 0:
                            if vpx[x, y][:3] in veg_in_colors:
                                ok = True
                        else:
                            wmin = max(0, x-near_radius); wmax = min(width-1, x+near_radius)
                            hmin = max(0, y-near_radius); hmax = min(height-1, y+near_radius)
                            for yy in range(hmin, hmax+1):
                                for xx in range(wmin, wmax+1):
                                    if vpx[xx, yy][:3] in veg_in_colors:
                                        ok = True; break
                                if ok: break
                        if not ok:
                            continue

                    # Spawn cluster around (x,y)
                    count = rr.randint(gmin, gmax)
                    for _g in range(count):
                        cx = x + (rr.randint(-jitter, jitter) if jitter>0 else 0)
                        cy = y + (rr.randint(-jitter, jitter) if jitter>0 else 0)
                        ox = cx + rr.randint(-radius, radius)
                        oy = cy + rr.randint(-radius, radius)
                        if 0 <= ox < width and 0 <= oy < height:
                            if colors_list:
                                cc = colors_list[rr.randrange(len(colors_list))]
                                opx[ox, oy] = cc + (255,)
                            else:
                                opx[ox, oy] = color + (255,)
                    placed = True
                    break
                # if not placed after attempts, skip
        else:
            for x in range(0, width, stride):
                for y in range(0, height, stride):
                    if tpx is not None and tpx[x, y][:3] == WATER:
                        continue
                    # road filter
                    if road_mode != "any" and rpx is not None:
                        m = _roads_pixel_mode(rpx[x, y])
                        if road_mode == "asphalt_only" and m != "asphalt":
                            continue
                        if road_mode == "non_asphalt" and m != "non_asphalt":
                            continue
                    if near_road_radius > 0 and rpx is not None:
                        ok_road = False
                        for yy in range(max(0, y-near_road_radius), min(height, y+near_road_radius+1)):
                            for xx in range(max(0, x-near_road_radius), min(width, x+near_road_radius+1)):
                                if rpx[xx, yy][3] > 0:
                                    ok_road = True; break
                            if ok_road: break
                        if not ok_road:
                            continue

                    # terrain inclusion
                    if terr_in and tpx is not None:
                        tname = _closest_terrain_name(tpx[x, y][:3])
                        if tname not in terr_in:
                            continue

                    # vegetation inclusion (exact match or nearby within radius)
                    if veg_in_colors and vpx is not None:
                        ok = False
                        if near_radius <= 0:
                            if vpx[x, y][:3] in veg_in_colors:
                                ok = True
                        else:
                            wmin = max(0, x-near_radius); wmax = min(width-1, x+near_radius)
                            hmin = max(0, y-near_radius); hmax = min(height-1, y+near_radius)
                            for yy in range(hmin, hmax+1):
                                for xx in range(wmin, wmax+1):
                                    if vpx[xx, yy][:3] in veg_in_colors:
                                        ok = True; break
                                if ok: break
                        if not ok:
                            continue

                    v = noise_utils.perlin2(x, y, scale=scale, octaves=octaves,
                                            persistence=persistence, lacunarity=lacunarity, seed=seed)
                    v = (v - vmin) / ((vmax - vmin) or 1.0)
                    if v >= thresh:
                        # spawn a tiny group around (x,y)
                        count = rr.randint(gmin, gmax)
                        for _ in range(count):
                            cx = x + (rr.randint(-jitter, jitter) if jitter>0 else 0)
                            cy = y + (rr.randint(-jitter, jitter) if jitter>0 else 0)
                            ox = cx + rr.randint(-radius, radius)
                            oy = cy + rr.randint(-radius, radius)
                            if 0 <= ox < width and 0 <= oy < height:
                                if colors_list:
                                    cc = colors_list[rr.randrange(len(colors_list))]
                                    opx[ox, oy] = cc + (255,)
                                else:
                                    opx[ox, oy] = color + (255,)

    return out
