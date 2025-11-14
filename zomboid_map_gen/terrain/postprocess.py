# zomboid_map_gen/terrain/postprocess.py
"""
Terrain post-processing passes:
- edge ragging: break up perfect outlines between terrain colors
- speckle: add small patches of other vanilla colors to reduce sameness
- erosion: push dirt/sand/dirt-grass into transition areas

All passes stay within the user's vanilla color set.
"""

from PIL import Image
import random
from ..utils import colors as base_colors

# unpack palette
WATER        = base_colors.VANILLA["water"][:3]
DARK_GRASS   = base_colors.VANILLA["dark_grass"][:3]
MED_GRASS    = base_colors.VANILLA["med_grass"][:3]
LIGHT_GRASS  = base_colors.VANILLA["light_grass"][:3]
DIRT         = base_colors.VANILLA["dirt"][:3]
DIRT_GRASS   = base_colors.VANILLA["dirt_grass"][:3]
SAND         = base_colors.VANILLA["sand"][:3]
GRAVEL_DIRT  = base_colors.VANILLA["gravel_dirt"][:3]


def _get_neighbors(img, x, y):
    w, h = img.size
    neigh = []
    if x > 0:
        neigh.append(img.getpixel((x - 1, y))[:3])
    if x < w - 1:
        neigh.append(img.getpixel((x + 1, y))[:3])
    if y > 0:
        neigh.append(img.getpixel((x, y - 1))[:3])
    if y < h - 1:
        neigh.append(img.getpixel((x, y + 1))[:3])
    return neigh


def _color_dist(c1, c2):
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])


def edge_ragging(img: Image.Image, strength: float = 0.5, rnd: random.Random | None = None) -> Image.Image:
    """
    Break up clean edges by letting neighbor colors invade.
    """
    w, h = img.size
    src = img
    out = img.copy()
    px = out.load()

    for y in range(h):
        for x in range(w):
            here = src.getpixel((x, y))[:3]
            neigh = _get_neighbors(src, x, y)
            # boundary: neighboring pixel is very different
            boundary_neighbors = [n for n in neigh if _color_dist(here, n) > 25]
            if not boundary_neighbors:
                continue

            r = rnd.random() if rnd else random.random()
            if r < strength * 0.6:
                new_col = random.choice(boundary_neighbors)
                px[x, y] = new_col + (255,)

    return out


def speckle(img: Image.Image, density: float = 0.01, rnd: random.Random | None = None) -> Image.Image:
    """
    Sprinkle small patches of nearby vanilla colors.
    """
    w, h = img.size
    out = img.copy()
    px = out.load()

    # don't speckle water, but we can speckle grass/dirt/sand
    candidates = [
        DARK_GRASS,
        MED_GRASS,
        LIGHT_GRASS,
        DIRT,
        DIRT_GRASS,
        SAND,
        GRAVEL_DIRT,
    ]

    total = w * h
    target = int(total * density)

    rr = rnd or random
    for _ in range(target):
        x = rr.randint(0, w - 1)
        y = rr.randint(0, h - 1)
        current = px[x, y][:3]

        if current == WATER:
            continue

        # choose a different but related color
        choices = [c for c in candidates if c != current]
        if not choices:
            continue
        new_col = rr.choice(choices)
        px[x, y] = new_col + (255,)

    return out


def erosion(img: Image.Image, strength: float = 0.5, rnd: random.Random | None = None) -> Image.Image:
    """
    Soft erosion:
    - near water -> more sand
    - mixed terrain edges -> dirt or dirt grass
    """
    w, h = img.size
    src = img
    out = img.copy()
    px = out.load()

    for y in range(h):
        for x in range(w):
            here = src.getpixel((x, y))[:3]
            neigh = _get_neighbors(src, x, y)

            # near water -> sand
            if any(_color_dist(n, WATER) < 12 for n in neigh):
                r = rnd.random() if rnd else random.random()
                if here != WATER and r < strength * 0.75:
                    px[x, y] = SAND + (255,)
                    continue

            # mixed edges -> dirt-ish
            if any(_color_dist(here, n) > 35 for n in neigh):
                r2 = rnd.random() if rnd else random.random()
                if r2 < strength * 0.5:
                    # 50/50 dirt vs dirt grass
                    r3 = rnd.random() if rnd else random.random()
                    if r3 < 0.5:
                        px[x, y] = DIRT + (255,)
                    else:
                        px[x, y] = DIRT_GRASS + (255,)

    return out

def apply_edge_ragging(img, amount: int = 1, probability: float = 0.35) -> Image.Image:
    w, h = img.size
    src = img.load()
    out = img.copy()
    dst = out.load()

    for y in range(h):
        for x in range(w):
            if random.random() < probability:
                jx = x + random.randint(-amount, amount)
                jy = y + random.randint(-amount, amount)

                # clamp
                if jx < 0: jx = 0
                if jx >= w: jx = w - 1
                if jy < 0: jy = 0
                if jy >= h: jy = h - 1

                dst[x, y] = src[jx, jy]
            else:
                dst[x, y] = src[x, y]

    return out


def apply_speckle(img, density: float = 0.01, strength: int = 18) -> Image.Image:
    w, h = img.size
    out = img.copy()
    px = out.load()

    for y in range(h):
        for x in range(w):
            if random.random() < density:
                r, g, b, *rest = px[x, y]
                dr = random.randint(-strength, strength)
                dg = random.randint(-strength, strength)
                db = random.randint(-strength, strength)
                r = max(0, min(255, r + dr))
                g = max(0, min(255, g + dg))
                b = max(0, min(255, b + db))
                if rest:
                    px[x, y] = (r, g, b, rest[0])
                else:
                    px[x, y] = (r, g, b)
    return out


def apply_erosion(img, radius: int = 1) -> Image.Image:
    w, h = img.size
    src = img.load()
    out = img.copy()
    dst = out.load()

    for y in range(h):
        for x in range(w):
            base = src[x, y]
            darkest = base
            darkest_lum = _lum(base)

            for ny in range(max(0, y - radius), min(h, y + radius + 1)):
                for nx in range(max(0, x - radius), min(w, x + radius + 1)):
                    c = src[nx, ny]
                    l = _lum(c)
                    if l < darkest_lum:
                        darkest_lum = l
                        darkest = c

            dst[x, y] = darkest

    return out


def apply_all(img: Image.Image, conf: dict) -> Image.Image:
    """
    Apply whatever the GUI/config says is enabled.
    Uses palette-safe variants to keep colours within the vanilla set.
    """
    terrain_conf = conf.get("terrain", {})
    pp_conf = terrain_conf.get("postprocess", {})

    edge_on = pp_conf.get("edge_ragging", True)
    speckle_on = pp_conf.get("speckle", True)
    erosion_on = pp_conf.get("erosion", True)

    # Optional overall strength knob; defaults are tuned inside each pass
    overall = float(pp_conf.get("strength", 0.6))
    overall = max(0.0, min(1.0, overall))

    out = img
    # deterministic local RNG for post passes
    seed = int(conf.get("seed", 0)) ^ 0xA5A5_1B
    rnd = random.Random(seed)
    # Allow per-effect overrides from config
    edge_strength = pp_conf.get("edge_strength")
    speckle_density = pp_conf.get("speckle_density")
    erosion_strength = pp_conf.get("erosion_strength")

    if edge_on:
        es = float(edge_strength) if edge_strength is not None else (0.35 + 0.45 * overall)
        es = max(0.0, min(1.0, es))
        out = edge_ragging(out, strength=es, rnd=rnd)
    if speckle_on:
        dens = float(speckle_density) if speckle_density is not None else (0.004 + 0.02 * overall)
        dens = max(0.0, dens)
        out = speckle(out, density=dens, rnd=rnd)
    if erosion_on:
        er = float(erosion_strength) if erosion_strength is not None else (0.35 + 0.45 * overall)
        er = max(0.0, min(1.0, er))
        out = erosion(out, strength=er, rnd=rnd)

    return out


def _lum(color):
    r, g, b = color[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b
