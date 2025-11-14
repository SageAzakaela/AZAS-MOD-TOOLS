# zomboid_map_gen/vegetation/vegetation_generator.py
"""
Vegetation renderer.

- generates a vegetation.png-style mask using the user's veg color scheme
- uses noise to decide which vegetation band to use
- can optionally respect terrain (no trees on water or asphalt)
"""

from PIL import Image
import math
from ..utils import noise_utils, colors as base_colors, seeds as seed_utils
from ..utils.parallel import split_range, run_process_map, cpu_count
from . import presets


# ---- Parallel worker (top-level for Windows spawn) ----
def _veg_noise_chunk_worker(x0, x1, width, height, scale, octaves, persistence, lac, layer_seed,
                            rot, offx, offy, use_tr_flag, ca_local, sa_local,
                            warp_enabled, warp_amount, warp_scale, warp_seed):
    vals = []
    cx_local = width/2.0; cy_local = height/2.0
    for x in range(x0, x1):
        rx = x - cx_local
        for y in range(height):
            if use_tr_flag:
                ry = y - cy_local
                tx = rx*ca_local - ry*sa_local; ty = rx*sa_local + ry*ca_local
                sx = tx + cx_local + offx; sy = ty + cy_local + offy
            else:
                sx, sy = x, y
            if warp_enabled and warp_amount>0:
                sx, sy = noise_utils.domain_warp_coords(sx, sy, amount=warp_amount, warp_scale=warp_scale, seed=warp_seed)
            v = noise_utils.perlin2(sx, sy, scale=scale, octaves=octaves,
                                    persistence=persistence, lacunarity=lac, seed=layer_seed)
            vals.append(v)
    return vals


# ordered list of vegetation colors from lowest to highest density
# (we'll map noise 0..1 into this list)
VEG_BANDS = [
    base_colors.VEG["none"][:3],               # 0
    base_colors.VEG["grass_some_trees"][:3],   # 1
    base_colors.VEG["light_long_grass"][:3],   # 2
    base_colors.VEG["trees_grass"][:3],        # 3
    base_colors.VEG["dense_trees_grass"][:3],  # 4
    base_colors.VEG["dense_forest"][:3],       # 5
    base_colors.VEG["bushes_grass"][:3],       # 6
    # you also have dead corn colors (optional sprinkle later)
]

# Skew thresholds so dense bands occupy less of the range by default
VEG_THRESH = [0.00, 0.12, 0.28, 0.52, 0.72, 0.88, 0.96, 1.01]


# terrain colors we SHOULD NOT overwrite with vegetation if respect_terrain=True
TERRAIN_BLOCKLIST = {
    base_colors.VANILLA["water"][:3],
    base_colors.VANILLA["light_asphalt"][:3],
    base_colors.VANILLA["dark_asphalt"][:3],
    base_colors.VANILLA["medium_asphalt"][:3],
}

ASPHALT_SET = {
    base_colors.VANILLA["light_asphalt"][:3],
    base_colors.VANILLA["dark_asphalt"][:3],
    base_colors.VANILLA["medium_asphalt"][:3],
}


def _get_canvas_size(conf: dict) -> tuple[int, int]:
    canvas_conf = conf.get("canvas", {})
    cell_size = canvas_conf.get("cell_size", 300)
    cells_x = canvas_conf.get("cells_x", 1)
    cells_y = canvas_conf.get("cells_y", 1)
    width = cell_size * cells_x
    height = cell_size * cells_y
    return width, height


def _terrain_pixel_blocked(terrain_img, x, y, respect: bool) -> bool:
    if not respect:
        return False
    if terrain_img is None:
        return False
    rgb = terrain_img.getpixel((x, y))[:3]
    return rgb in TERRAIN_BLOCKLIST


def _closest_terrain_name(rgb):
    candidates = {
        "dark_grass": base_colors.VANILLA["dark_grass"][:3],
        "med_grass": base_colors.VANILLA["med_grass"][:3],
        "light_grass": base_colors.VANILLA["light_grass"][:3],
        "sand": base_colors.VANILLA["sand"][:3],
        "dirt": base_colors.VANILLA["dirt"][:3],
    }
    best_name = None; best_d = 1e9
    for name, col in candidates.items():
        d = abs(rgb[0]-col[0]) + abs(rgb[1]-col[1]) + abs(rgb[2]-col[2])
        if d < best_d:
            best_d = d; best_name = name
    return best_name


def _generate_layers(conf: dict, width: int, height: int, terrain_img=None):
    veg_conf = conf.get("vegetation", {})
    # Allow UI to disable layers while keeping them in config
    if veg_conf.get("use_layers") is False:
        return None
    master_seed = int(conf.get("seed", 0)) + int(veg_conf.get("seed_offset", 0))
    layers = veg_conf.get("layers", [])
    if not layers:
        return None

    img = Image.new("RGBA", (width, height))
    px = img.load()

    # Precompute per-layer noise min/max so thresholds are meaningful (parallelized)
    noises = []
    vmins, vmaxs = [], []

    tr = veg_conf.get("transform", {})
    rot = float(tr.get("rotation", 0.0)); offx=float(tr.get("offset_x",0.0)); offy=float(tr.get("offset_y",0.0))
    use_tr = (rot % 360) != 0 or offx != 0 or offy != 0
    cx = width/2.0; cy = height/2.0
    ca = math.cos(math.radians(rot)); sa = math.sin(math.radians(rot))

    def _sample(seed, scale, octaves, persistence, lacunarity, x, y):
        if use_tr:
            rx, ry = x - cx, y - cy
            tx = rx*ca - ry*sa; ty = rx*sa + ry*ca
            x, y = tx + cx + offx, ty + cy + offy
        return noise_utils.perlin2(x, y, scale=scale, octaves=octaves,
                                   persistence=persistence, lacunarity=lacunarity, seed=seed)

    # noise chunk worker defined at top-level: _veg_noise_chunk_worker

    for layer in layers:
        scale = int(layer.get("scale", 60)); octaves = int(layer.get("octaves", 5))
        persistence = float(layer.get("persistence", 0.55)); lac = float(layer.get("lacunarity", 2.0))
        layer_seed = layer.get("seed")
        if layer_seed is None:
            layer_seed = seed_utils.derive_seed(master_seed, layer.get("name", "veg_layer"))
        warp = layer.get("warp", {})
        warp_enabled = bool(warp.get("enabled", False))
        warp_amount = float(warp.get("amount", 0.0)); warp_scale=float(warp.get("scale", 100.0))
        warp_seed = int(warp.get("seed", layer_seed))

        chunks = split_range(width, cpu_count())
        ca_local, sa_local = ca, sa
        vals_parts = run_process_map(
            _veg_noise_chunk_worker,
            [
                (a, b, width, height, float(scale), int(octaves), float(persistence), float(lac), int(layer_seed),
                 float(rot), float(offx), float(offy), bool(use_tr), float(ca_local), float(sa_local),
                 bool(warp_enabled), float(warp_amount), float(warp_scale), int(warp_seed))
                for a, b in chunks
            ]
        )
        vals = []
        for part in vals_parts:
            vals.extend(part)
        vmin = min(vals); vmax = max(vals)
        noises.append(vals); vmins.append(vmin); vmaxs.append(vmax)

    # Paint in order; later layers win
    for li, layer in enumerate(layers):
        color = tuple(layer.get("color", base_colors.VEG["light_long_grass"]))
        threshold = float(layer.get("threshold", 0.5))
        respect = bool(layer.get("respect_terrain", True))
        terr_in = set(layer.get("terrain_in", []))
        vals = noises[li]; vmin=vmins[li]; vmax=vmaxs[li]; vr = (vmax - vmin) or 1.0
        i=0
        for x in range(width):
            for y in range(height):
                if _terrain_pixel_blocked(terrain_img, x, y, respect):
                    i+=1; continue
                if terr_in and terrain_img is not None:
                    tname = _closest_terrain_name(terrain_img.getpixel((x,y))[:3])
                    if tname not in terr_in:
                        i+=1; continue
                v = (vals[i] - vmin)/vr; i+=1
                if v >= threshold:
                    px[x, y] = color
    return img


def generate(conf: dict, terrain_img=None):
    veg_conf = conf.get("vegetation", {})
    preset_vals = presets.get_preset(veg_conf.get("preset", "overgrown"))

    width, height = _get_canvas_size(conf)

    seed = int(conf.get("seed", 0)) + int(veg_conf.get("seed_offset", 0)) + 999
    scale = veg_conf.get("scale", preset_vals["scale"])
    octaves = veg_conf.get("octaves", preset_vals["octaves"])
    persistence = veg_conf.get("persistence", preset_vals["persistence"])
    lacunarity = veg_conf.get("lacunarity", preset_vals["lacunarity"])
    respect_terrain = veg_conf.get("respect_terrain", True)

    # Layered vegetation mode if present
    # Build layered overlay (if enabled) and banded base, then mix according to mode
    mode = (veg_conf.get("mode") or ("layered" if veg_conf.get("layers") else "banded")).lower()
    layered = _generate_layers(conf, width, height, terrain_img)

    # Always compute banded base (used for banded or mixed)
    img = Image.new("RGBA", (width, height))
    px = img.load()

    # Two-pass normalization using transformed sample coords to ensure we use
    # the full band range and get more than just 2–3 colors.
    tr = conf.get("vegetation", {}).get("transform", {})
    rot = float(tr.get("rotation", 0.0))
    offx = float(tr.get("offset_x", 0.0))
    offy = float(tr.get("offset_y", 0.0))
    use_tr = (rot % 360) != 0 or offx != 0 or offy != 0
    cx = width / 2.0; cy = height / 2.0
    ca = math.cos(math.radians(rot)); sa = math.sin(math.radians(rot))

    def sample_at(ix, iy):
        if use_tr:
            rx = ix - cx; ry = iy - cy
            tx = rx * ca - ry * sa
            ty = rx * sa + ry * ca
            sx, sy = tx + cx + offx, ty + cy + offy
        else:
            sx, sy = ix, iy
        return noise_utils.perlin2(
            sx, sy,
            scale=scale,
            octaves=octaves,
            persistence=persistence,
            lacunarity=lacunarity,
            seed=seed,
        )

    vmin = 1e9
    vmax = -1e9
    for x in range(width):
        for y in range(height):
            vv = sample_at(x, y)
            if vv < vmin: vmin = vv
            if vv > vmax: vmax = vv
    vrange = vmax - vmin if vmax != vmin else 1.0
    bands_count = len(VEG_BANDS)

    # Terrain-aware density bias: push noise up on dark grass, down on light
    bias_conf = conf.get("vegetation", {}).get("terrain_bias", {
        "dark_grass": 0.18,
        "med_grass": 0.08,
        "light_grass": -0.10,
        "sand": -0.22,
    })

    def terrain_bias(x, y):
        if terrain_img is None:
            return 0.0
        rgb = terrain_img.getpixel((x, y))[:3]
        # quick nearest match among key colors
        candidates = {
            "dark_grass": base_colors.VANILLA["dark_grass"][:3],
            "med_grass": base_colors.VANILLA["med_grass"][:3],
            "light_grass": base_colors.VANILLA["light_grass"][:3],
            "sand": base_colors.VANILLA["sand"][:3],
            "dirt": base_colors.VANILLA["dirt"][:3],
        }
        best_name = None; best_d = 1e9
        for name, col in candidates.items():
            d = abs(rgb[0]-col[0]) + abs(rgb[1]-col[1]) + abs(rgb[2]-col[2])
            if d < best_d:
                best_d = d; best_name = name
        return float(bias_conf.get(best_name, 0.0))

    for x in range(width):
        for y in range(height):
            # optional terrain-aware rule
            if _terrain_pixel_blocked(terrain_img, x, y, respect_terrain):
                px[x, y] = base_colors.VEG["none"]
                continue

            vv = sample_at(x, y)
            v = (vv - vmin) / vrange  # 0..1 across the whole image
            # terrain-aware bias
            v = max(0.0, min(1.0, v + terrain_bias(x, y)))

            # map via skewed thresholds to reduce dense coverage
            idx = 0
            while idx < bands_count and v >= VEG_THRESH[idx + 1]:
                idx += 1

            col = VEG_BANDS[idx]
            px[x, y] = col + (255,)

    if mode == "banded" or layered is None:
        return img

    if mode == "layered":
        return layered

    # mixed: replace base with layered pixel with probability = wetness if layered has content
    wet = float(veg_conf.get("mixed_wetness", 0.5))
    wet = max(0.0, min(1.0, wet))
    lpx = layered.load()
    # coordinate‑based deterministic RNG
    import random as _random
    rr = _random.Random(int(seed))
    for x in range(width):
        for y in range(height):
            if lpx[x, y][3] > 0:
                # derive per‑pixel decision from coords to keep deterministic
                rr.seed((x * 73856093) ^ (y * 19349663) ^ int(seed))
                if rr.random() < wet:
                    px[x, y] = lpx[x, y]

    return img

