"""
Post-process passes for roads:
- potholes (jagged, density-based) CLIPPED to asphalt mask
- parking lot helper
- vegetation carve
- dirt transition sprinkle
"""

import random
from PIL import Image, ImageDraw, ImageChops
from typing import Optional
from ..utils import colors as base_colors

# road-ish colors we allow potholes on
ASPHALTS = {
    base_colors.VANILLA["dark_asphalt"][:3],
    base_colors.VANILLA["medium_asphalt"][:3],
    base_colors.VANILLA["light_asphalt"][:3],
}

# road-ish colors we DO NOT pothole
DIRTLIKE = {
    base_colors.VANILLA["dirt"][:3],
    base_colors.VANILLA["gravel_dirt"][:3],
    base_colors.VANILLA["sand"][:3],
}

DARK_POTHOLE = base_colors.VANILLA["dark_pothole"][:3]
LIGHT_POTHOLE = base_colors.VANILLA["light_pothole"][:3]


def _asphalt_mask(road_img: Image.Image) -> Image.Image:
    """
    Build an L mask (0-255) where pixel is one of the asphalt colors.
    """
    w, h = road_img.size
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    rp = road_img.load()
    for y in range(h):
        for x in range(w):
            px = rp[x, y]
            if len(px) == 4 and px[3] > 0 and px[:3] in ASPHALTS:
                mp[x, y] = 255
    return mask


def apply_potholes_noise_jagged_clipped(road_img: Image.Image, density=0.02, seed=None) -> Image.Image:
    """
    Place small jagged shapes on asphalt areas only, clipping to asphalt mask so
    potholes never extend beyond the road pixels themselves.
    """
    if density <= 0:
        return road_img

    w, h = road_img.size
    rnd = random.Random(seed) if seed is not None else random

    asphalt_mask = _asphalt_mask(road_img)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rp = road_img.load()

    num_attempts = int(w * h * density * 0.15)

    for _ in range(num_attempts):
        x = rnd.randint(0, w - 1)
        y = rnd.randint(0, h - 1)
        base_px = rp[x, y]
        base_rgb = base_px[:3]
        if base_rgb not in ASPHALTS:
            continue

        if base_rgb in (base_colors.VANILLA["dark_asphalt"][:3], base_colors.VANILLA["medium_asphalt"][:3]):
            pothole_col = DARK_POTHOLE
        else:
            pothole_col = LIGHT_POTHOLE

        points = []
        radius = rnd.randint(2, 4)
        for _ in range(rnd.randint(4, 7)):
            ox = x + rnd.randint(-radius, radius)
            oy = y + rnd.randint(-radius, radius)
            points.append((ox, oy))
        d.polygon(points, fill=pothole_col + (255,))

    # clip pothole layer to asphalt mask
    layer_alpha = layer.split()[3]
    combined_mask = ImageChops.multiply(layer_alpha, asphalt_mask)
    road_img.paste(layer, (0, 0), combined_mask)
    return road_img


def add_parking_lot_rect(lots_img: Image.Image, x, y, w, h, color=(255, 0, 0, 255)):
    d = ImageDraw.Draw(lots_img)
    d.rectangle([x, y, x + w, y + h], fill=color)


def carve_vegetation_mask(veg_img: Optional[Image.Image], roads_img: Optional[Image.Image],
                          skip_dirt: bool = True) -> Optional[Image.Image]:
    """
    Remove vegetation where roads are present.
    If skip_dirt=True, don't carve for dirt-like roads.
    """
    if veg_img is None or roads_img is None:
        return veg_img

    w, h = veg_img.size
    if roads_img.size != (w, h):
        return veg_img

    none_col = base_colors.VEG["none"]
    vpx = veg_img.load()
    rpx = roads_img.load()

    for y in range(h):
        for x in range(w):
            r = rpx[x, y]
            if len(r) == 4 and r[3] > 0:
                base = r[:3]
                if skip_dirt and base in DIRTLIKE:
                    continue
                vpx[x, y] = none_col

    return veg_img


def sprinkle_dirt_transitions(roads_img: Image.Image, box=2):
    """
    Where dirt-like roads intersect asphalt roads, sprinkle a bit of dirt.
    This is light and cosmetic.
    """
    w, h = roads_img.size
    px = roads_img.load()

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            here = px[x, y]
            if here[3] == 0:
                continue

            base = here[:3]
            neigh = [px[x - 1, y], px[x + 1, y], px[x, y - 1], px[x, y + 1]]
            colors = {n[:3] for n in neigh if n[3] > 0}
            if len(colors) >= 2:
                if (base in ASPHALTS and any((n[:3] in DIRTLIKE) for n in neigh if n[3] > 0)) or \
                   (base in DIRTLIKE and any((n[:3] in ASPHALTS) for n in neigh if n[3] > 0)):
                    dirt_col = base_colors.VANILLA["dirt"][:3]
                    for dx in range(-box, box + 1):
                        xx = x + dx
                        yy = y + 1
                        if 0 <= xx < w and 0 <= yy < h:
                            px[xx, yy] = dirt_col + (255,)
